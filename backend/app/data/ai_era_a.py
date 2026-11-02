"""AI-Era interview content, part A: code comprehension, AI-assisted coding, debugging, production repos.

Lines ending with a `#!BUG <label>` / `//!BUG <label>` / `--!BUG <label>` marker are planted issues; the
loader strips the marker and records the line number as the answer key.
"""

INVENTORY = '''"""Inventory reservation service used by the checkout API."""

import logging
import time
import uuid
from dataclasses import dataclass, field, replace

log = logging.getLogger("inventory")

CACHE_TTL_SECONDS = 30
MAX_RETRIES = 3


class OutOfStock(Exception):
    pass


class PaymentFailed(Exception):
    pass


@dataclass
class Product:
    sku: str
    name: str
    price: float  #!BUG Money stored as float -> rounding errors; use Decimal or integer paise/cents
    stock: int
    reserved: int = 0

    @property
    def available(self) -> int:
        return self.stock - self.reserved


@dataclass
class OrderItem:
    sku: str
    qty: int


@dataclass
class Order:
    id: str
    user_id: int
    items: list[OrderItem]
    status: str = "pending"
    total: float = 0.0
    created_at: float = field(default_factory=time.time)


class TTLCache:
    def __init__(self, ttl: int):
        self.ttl = ttl
        self._data: dict[str, tuple[float, object]] = {}

    def get(self, key):
        hit = self._data.get(key)
        if hit is None:
            return None
        expires, value = hit
        if expires < time.time():
            del self._data[key]
            return None
        return value

    def set(self, key, value):
        self._data[key] = (time.time() + self.ttl, value)

    def delete(self, key):
        self._data.pop(key, None)


class ProductRepository:
    """In-memory stand-in for the products table."""

    def __init__(self, products: list[Product]):
        self.products = products

    def find(self, sku: str) -> Product | None:
        for p in self.products:  #!BUG Linear scan on every lookup -> O(n*m) per order; index by sku in a dict
            if p.sku == sku:
                return p
        return None

    def save(self, product: Product) -> None:
        log.debug("saved %s stock=%s reserved=%s", product.sku, product.stock, product.reserved)


class PaymentGateway:
    def __init__(self, client):
        self.client = client

    def charge(self, user_id: int, amount: float, idempotency_key: str | None = None) -> str:
        response = self.client.post("/charges", json={"user": user_id, "amount": amount, "key": idempotency_key})
        if response.status_code != 200:
            raise PaymentFailed(response.text)
        return response.json()["charge_id"]


class EventBus:
    def __init__(self):
        self.handlers = {}

    def subscribe(self, topic, handler):
        self.handlers.setdefault(topic, []).append(handler)

    def publish(self, topic, payload):
        for handler in self.handlers.get(topic, []):
            try:
                handler(payload)
            except Exception:
                log.exception("handler failed for %s", topic)


class InventoryService:
    def __init__(self, repo: ProductRepository, payments: PaymentGateway, events: EventBus):
        self.repo = repo
        self.payments = payments
        self.events = events
        self.cache = TTLCache(CACHE_TTL_SECONDS)

    def get_product(self, sku: str) -> Product:
        cached = self.cache.get(sku)
        if cached is not None:
            return cached
        product = self.repo.find(sku)
        if product is None:
            raise KeyError(sku)
        self.cache.set(sku, replace(product))
        return product

    def available(self, sku: str) -> int:
        return self.get_product(sku).available

    def _check_stock(self, items: list[OrderItem]) -> None:
        for item in items:
            if item.qty <= 0:
                raise ValueError(f"invalid quantity for {item.sku}")
            product = self.get_product(item.sku)
            if not product.available > item.qty:  #!BUG Off-by-one: rejects an order for exactly the remaining stock (should be >=)
                raise OutOfStock(item.sku)

    def _reserve(self, items: list[OrderItem]) -> list[tuple[Product, int]]:
        reserved = []
        for item in items:
            product = self.repo.find(item.sku)
            product.reserved += item.qty
            self.repo.save(product)  #!BUG Cache is never invalidated after reserving -> stale availability for 30s, overselling
            reserved.append((product, item.qty))
        return reserved

    def _release(self, reserved: list[tuple[Product, int]]) -> None:
        for product, qty in reserved:
            product.reserved -= qty
            self.repo.save(product)

    def _total(self, items: list[OrderItem]) -> float:
        total = 0.0
        for item in items:
            total += self.get_product(item.sku).price * item.qty
        return round(total, 2)

    def _charge_with_retry(self, order: Order) -> str:
        attempt = 0
        while True:
            try:
                return self.payments.charge(order.user_id, order.total)  #!BUG No idempotency key: a retry after a timeout can charge the customer twice
            except Exception as e:  #!BUG Retries every exception, including card declines (PaymentFailed) that will never succeed
                attempt += 1
                if attempt >= MAX_RETRIES:
                    raise PaymentFailed(str(e)) from e
                time.sleep(2 ** attempt)

    def reserve_order(self, user_id: int, items: list[OrderItem] = []) -> Order:  #!BUG Mutable default argument shared across calls
        if not items:
            raise ValueError("empty order")
        order = Order(id=str(uuid.uuid4()), user_id=user_id, items=items)
        self._check_stock(items)  #!BUG Check-then-act race: two concurrent orders can both pass the check before either reserves (needs a lock / atomic update)
        reserved = self._reserve(items)
        order.total = self._total(items)
        try:
            charge_id = self._charge_with_retry(order)
        except PaymentFailed:
            self._release(reserved)
            order.status = "payment_failed"
            self.events.publish("order.failed", {"order": order.id})
            return order
        for product, qty in reserved:
            product.stock -= qty
            product.reserved -= qty
            self.repo.save(product)
        order.status = "confirmed"
        self.events.publish("order.confirmed", {"order": order.id, "charge": charge_id, "total": order.total})
        log.info("order %s confirmed for user %s", order.id, user_id)
        return order

    def restock(self, sku: str, qty: int) -> None:
        product = self.repo.find(sku)
        if product is None:
            raise KeyError(sku)
        product.stock += qty
        self.repo.save(product)
        self.cache.delete(sku)
        self.events.publish("product.restocked", {"sku": sku, "qty": qty})

    def low_stock_report(self, threshold: int = 5) -> list[str]:
        report = []
        for p in self.repo.products:
            if p.available < threshold:
                report.append(f"{p.sku}: {p.available} left")
        return sorted(report)
'''

RATE_LIMITER = '''// Express middleware: per-client sliding-window rate limiter.
const WINDOW_MS = 60_000;
const DEFAULT_LIMIT = 100;

const hits = new Map(); // clientId -> number[] of request timestamps

function clientId(req) {
  const forwarded = req.headers["x-forwarded-for"];
  if (forwarded) return forwarded.split(",")[0].trim(); //!BUG Trusts a client-controlled header: attackers rotate X-Forwarded-For to bypass the limit
  return req.socket.remoteAddress;
}

function prune(timestamps, now) {
  while (timestamps.length && timestamps[0] <= now - WINDOW_MS) {
    timestamps.shift(); //!BUG Array.shift is O(n); pruning becomes O(n^2) for busy clients (use a ring buffer / index pointer)
  }
}

function rateLimit({ limit = DEFAULT_LIMIT, routes = {} } = {}) {
  return function (req, res, next) {
    const now = Date.now();
    const id = clientId(req);
    const routeLimit = routes[req.path] || limit; //!BUG Per-route limits share one bucket per client, and exact req.path never matches parameterised routes
    let timestamps = hits.get(id);
    if (!timestamps) {
      timestamps = [];
      hits.set(id, timestamps); //!BUG Keys are never evicted: one entry per IP forever -> memory leak
    }
    prune(timestamps, now);
    if (timestamps.length > routeLimit) { //!BUG Off-by-one: allows limit + 1 requests per window (should be >=)
      const retryAfter = Math.ceil((timestamps[0] + WINDOW_MS - now) / 1000);
      res.set("Retry-After", String(retryAfter));
      return res.status(429).json({ error: "Too many requests" });
    }
    timestamps.push(now);
    res.set("X-RateLimit-Remaining", String(routeLimit - timestamps.length));
    next();
  };
}

function stats() {
  let total = 0;
  for (const [, ts] of hits) total += ts.length;
  return { clients: hits.size, tracked: total };
}

module.exports = { rateLimit, stats, _hits: hits };
'''

# ---------------------------------------------------------------- production repos
REACT_REPO = [
    ("src/main.tsx", "tsx", '''import React from "react";
import ReactDOM from "react-dom/client";
import { AuthProvider } from "./context/AuthContext";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>,
);
'''),
    ("src/context/AuthContext.tsx", "tsx", '''import { createContext, useContext, useState } from "react";

interface Auth { token: string | null; login: (t: string) => void; logout: () => void }
const AuthContext = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem("token"));
  const login = (t: string) => { localStorage.setItem("token", t); setToken(t); };
  const logout = () => { localStorage.removeItem("token"); setToken(null); };
  return <AuthContext.Provider value={{ token, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
'''),
    ("src/api/client.ts", "ts", '''const BASE = import.meta.env.VITE_API_URL ?? "/api";

export async function request<T>(path: string, token: string | null, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401) throw new Error("unauthorized");
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.status === 204 ? (undefined as T) : res.json();
}

export interface Task { id: number; title: string; done: boolean }

export const tasksApi = {
  list: (token: string | null) => request<Task[]>("/tasks", token),
  create: (token: string | null, title: string) =>
    request<Task>("/tasks", token, { method: "POST", body: JSON.stringify({ title }) }),
  toggle: (token: string | null, task: Task) =>
    request<Task>(`/tasks/${task.id}`, token, { method: "PATCH", body: JSON.stringify({ done: !task.done }) }),
};
'''),
    ("src/hooks/useTasks.ts", "ts", '''import { useCallback, useEffect, useState } from "react";
import { Task, tasksApi } from "../api/client";
import { useAuth } from "../context/AuthContext";

export function useTasks() {
  const { token, logout } = useAuth();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    tasksApi.list(token).then(setTasks).catch((e) => {
      if (e.message === "unauthorized") logout();
      else setError(e.message);
    });
  }, [token, logout]);

  const add = useCallback(async (title: string) => {
    const created = await tasksApi.create(token, title);
    setTasks((prev) => [...prev, created]);
  }, [token]);

  const toggle = useCallback(async (task: Task) => {
    setTasks((prev) => prev.map((t) => (t.id === task.id ? { ...t, done: !t.done } : t)));
    try {
      await tasksApi.toggle(token, task);
    } catch {
      setTasks((prev) => prev.map((t) => (t.id === task.id ? task : t)));
      setError("Could not update task");
    }
  }, [token]);

  return { tasks, error, add, toggle };
}
'''),
    ("src/App.tsx", "tsx", '''import { useState } from "react";
import { useAuth } from "./context/AuthContext";
import { useTasks } from "./hooks/useTasks";
import TaskList from "./components/TaskList";
import Login from "./components/Login";

export default function App() {
  const { token } = useAuth();
  if (!token) return <Login />;
  return <Board />;
}

function Board() {
  const { tasks, error, add, toggle } = useTasks();
  const [title, setTitle] = useState("");
  return (
    <main>
      <form onSubmit={(e) => { e.preventDefault(); if (title.trim()) add(title).then(() => setTitle("")); }}>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="New task" />
        <button>Add</button>
      </form>
      {error && <p role="alert">{error}</p>}
      <TaskList tasks={tasks} onToggle={toggle} />
    </main>
  );
}
'''),
    ("src/components/TaskList.tsx", "tsx", '''import { Task } from "../api/client";
import TaskItem from "./TaskItem";

export default function TaskList({ tasks, onToggle }: { tasks: Task[]; onToggle: (t: Task) => void }) {
  if (tasks.length === 0) return <p>No tasks yet</p>;
  return (
    <ul>
      {tasks.map((t, i) => <TaskItem key={i} task={t} onToggle={onToggle} />)}
    </ul>
  );
}
'''),
    ("src/components/TaskItem.tsx", "tsx", '''import { memo } from "react";
import { Task } from "../api/client";

function TaskItem({ task, onToggle }: { task: Task; onToggle: (t: Task) => void }) {
  return (
    <li>
      <label>
        <input type="checkbox" checked={task.done} onChange={() => onToggle(task)} />
        <span style={{ textDecoration: task.done ? "line-through" : "none" }}>{task.title}</span>
      </label>
    </li>
  );
}

export default memo(TaskItem);
'''),
]

FASTAPI_REPO = [
    ("app/main.py", "python", '''from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from .routers import books

app = FastAPI(title="Bookstore API")
app.add_middleware(CORSMiddleware, allow_origins=["https://bookstore.example"], allow_methods=["*"], allow_headers=["*"])
Base.metadata.create_all(engine)
app.include_router(books.router, prefix="/api")
'''),
    ("app/db.py", "python", '''from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine("postgresql+psycopg://app:app@db/bookstore", pool_size=10, max_overflow=5)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''),
    ("app/models.py", "python", '''from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Author(Base):
    __tablename__ = "authors"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))


class Book(Base):
    __tablename__ = "books"
    id: Mapped[int] = mapped_column(primary_key=True)
    isbn: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    stock: Mapped[int] = mapped_column(default=0)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))
    author: Mapped[Author] = relationship(lazy="joined")
'''),
    ("app/schemas.py", "python", '''from decimal import Decimal

from pydantic import BaseModel, Field


class BookIn(BaseModel):
    isbn: str = Field(pattern=r"^\\d{13}$")
    title: str = Field(min_length=1, max_length=200)
    price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock: int = Field(0, ge=0)
    author_id: int


class BookOut(BaseModel):
    id: int
    isbn: str
    title: str
    price: Decimal
    stock: int
    author_name: str
'''),
    ("app/repositories/book_repo.py", "python", '''from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Book


class BookRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, book_id: int) -> Book | None:
        return self.db.get(Book, book_id)

    def by_isbn(self, isbn: str) -> Book | None:
        return self.db.scalar(select(Book).where(Book.isbn == isbn))

    def list(self, limit: int, offset: int) -> list[Book]:
        return list(self.db.scalars(select(Book).order_by(Book.id).limit(limit).offset(offset)))

    def add(self, book: Book) -> Book:
        self.db.add(book)
        self.db.flush()
        return book
'''),
    ("app/services/book_service.py", "python", '''from fastapi import HTTPException

from ..models import Book
from ..repositories.book_repo import BookRepository
from ..schemas import BookIn, BookOut


def to_out(book: Book) -> BookOut:
    return BookOut(id=book.id, isbn=book.isbn, title=book.title, price=book.price, stock=book.stock,
                   author_name=book.author.name)


class BookService:
    def __init__(self, repo: BookRepository):
        self.repo = repo

    def create(self, data: BookIn) -> BookOut:
        if self.repo.by_isbn(data.isbn):
            raise HTTPException(409, "ISBN already exists")
        book = self.repo.add(Book(**data.model_dump()))
        self.repo.db.commit()
        self.repo.db.refresh(book)
        return to_out(book)

    def list(self, page: int, size: int) -> list[BookOut]:
        return [to_out(b) for b in self.repo.list(size, (page - 1) * size)]
'''),
    ("app/routers/books.py", "python", '''from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..db import get_db
from ..repositories.book_repo import BookRepository
from ..schemas import BookIn, BookOut
from ..services.book_service import BookService, to_out

router = APIRouter(prefix="/books", tags=["books"])


def get_service(db: Session = Depends(get_db)) -> BookService:
    return BookService(BookRepository(db))


@router.get("", response_model=list[BookOut])
def list_books(page: int = Query(1, ge=1), size: int = Query(20, le=100), svc: BookService = Depends(get_service)):
    return svc.list(page, size)


@router.get("/{book_id}", response_model=BookOut)
def get_book(book_id: int, svc: BookService = Depends(get_service)):
    book = svc.repo.get(book_id)
    if book is None:
        raise HTTPException(404, "Book not found")
    return to_out(book)


@router.post("", response_model=BookOut, status_code=201)
def create_book(body: BookIn, svc: BookService = Depends(get_service)):
    return svc.create(body)
'''),
]

SPRING_REPO = [
    ("src/main/resources/application.yml", "yaml", '''spring:
  datasource:
    url: jdbc:postgresql://db:5432/payments
    hikari:
      maximum-pool-size: 20
  jpa:
    open-in-view: false
    hibernate:
      ddl-auto: validate
payments:
  gateway-url: https://gateway.example.com
  timeout-ms: 3000
'''),
    ("src/main/java/com/acme/payments/Payment.java", "java", '''package com.acme.payments;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;

@Entity
@Table(name = "payments", uniqueConstraints = @UniqueConstraint(columnNames = "idempotencyKey"))
public class Payment {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    private String idempotencyKey;
    private Long orderId;
    private BigDecimal amount;
    @Enumerated(EnumType.STRING)
    private Status status = Status.PENDING;
    private String gatewayRef;
    private Instant createdAt = Instant.now();

    public enum Status { PENDING, SUCCEEDED, FAILED }

    protected Payment() {}
    public Payment(String key, Long orderId, BigDecimal amount) {
        this.idempotencyKey = key; this.orderId = orderId; this.amount = amount;
    }
    public Long getId() { return id; }
    public Status getStatus() { return status; }
    public BigDecimal getAmount() { return amount; }
    public void succeed(String ref) { this.status = Status.SUCCEEDED; this.gatewayRef = ref; }
    public void fail() { this.status = Status.FAILED; }
}
'''),
    ("src/main/java/com/acme/payments/PaymentRepository.java", "java", '''package com.acme.payments;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface PaymentRepository extends JpaRepository<Payment, Long> {
    Optional<Payment> findByIdempotencyKey(String idempotencyKey);
}
'''),
    ("src/main/java/com/acme/payments/GatewayClient.java", "java", '''package com.acme.payments;

import java.math.BigDecimal;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class GatewayClient {
    private final RestClient http;

    public GatewayClient(@Value("${payments.gateway-url}") String url, @Value("${payments.timeout-ms}") int timeoutMs) {
        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(timeoutMs));
        factory.setReadTimeout(Duration.ofMillis(timeoutMs));
        this.http = RestClient.builder().baseUrl(url).requestFactory(factory).build();
    }

    public String charge(String idempotencyKey, BigDecimal amount) {
        record ChargeResponse(String reference) {}
        return http.post().uri("/charges")
            .header("Idempotency-Key", idempotencyKey)
            .body(java.util.Map.of("amount", amount))
            .retrieve().body(ChargeResponse.class).reference();
    }
}
'''),
    ("src/main/java/com/acme/payments/PaymentService.java", "java", '''package com.acme.payments;

import java.math.BigDecimal;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestClientException;

@Service
public class PaymentService {
    private final PaymentRepository repo;
    private final GatewayClient gateway;

    public PaymentService(PaymentRepository repo, GatewayClient gateway) {
        this.repo = repo;
        this.gateway = gateway;
    }

    @Transactional
    public Payment pay(String idempotencyKey, Long orderId, BigDecimal amount) {
        var existing = repo.findByIdempotencyKey(idempotencyKey);
        if (existing.isPresent()) return existing.get();
        if (amount.signum() <= 0) throw new IllegalArgumentException("amount must be positive");

        var payment = repo.save(new Payment(idempotencyKey, orderId, amount));
        try {
            payment.succeed(gateway.charge(idempotencyKey, amount));
        } catch (RestClientException e) {
            payment.fail();
        }
        return payment;
    }
}
'''),
    ("src/main/java/com/acme/payments/PaymentController.java", "java", '''package com.acme.payments;

import jakarta.validation.Valid;
import jakarta.validation.constraints.*;
import java.math.BigDecimal;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/payments")
public class PaymentController {
    private final PaymentService service;

    public PaymentController(PaymentService service) { this.service = service; }

    public record PayRequest(@NotNull Long orderId, @NotNull @Positive BigDecimal amount) {}

    @PostMapping
    public ResponseEntity<?> pay(@RequestHeader("Idempotency-Key") String key, @Valid @RequestBody PayRequest req) {
        var p = service.pay(key, req.orderId(), req.amount());
        var status = p.getStatus() == Payment.Status.SUCCEEDED ? 201 : 402;
        return ResponseEntity.status(status).body(java.util.Map.of("id", p.getId(), "status", p.getStatus()));
    }
}
'''),
    ("src/main/java/com/acme/payments/GlobalExceptionHandler.java", "java", '''package com.acme.payments;

import org.springframework.http.*;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;

@RestControllerAdvice
public class GlobalExceptionHandler {
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ProblemDetail> invalid(MethodArgumentNotValidException e) {
        return ResponseEntity.badRequest().body(ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, "Invalid request"));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ProblemDetail> bad(IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(ProblemDetail.forStatusAndDetail(HttpStatus.BAD_REQUEST, e.getMessage()));
    }
}
'''),
]


def _ai_file(code: str) -> tuple:
    return ("ai_answer.py", "python", code, True)


EXERCISES_A = [
    # ------------------------------------------------------------------ 1. Code Comprehension Lab
    {
        "id": "comp-inventory", "section": "comprehension", "title": "Inventory reservation service",
        "difficulty": "Hard", "minutes": 40,
        "summary": "A ~200-line checkout service with caching, retries and events. Explain it, then hunt the bugs.",
        "context": "You've joined the checkout team. This service reserves stock and charges the customer. "
                   "Production has reported occasional overselling and a few double charges.",
        "files": [("inventory_service.py", "python", INVENTORY)],
        "tasks": [
            {"id": "explain", "kind": "text", "prompt": "Explain what reserve_order() does end-to-end, in order.",
             "rubric": [("Validates the order (empty / quantity)", r"valid|empty|quantit"),
                        ("Checks stock availability", r"check.*stock|availab|out ?of ?stock"),
                        ("Reserves stock before charging", r"reserv"),
                        ("Computes the total", r"total|price"),
                        ("Charges payment with retries", r"charg|payment|retr"),
                        ("Releases the reservation on payment failure", r"releas|roll ?back|undo"),
                        ("Commits stock and publishes an event", r"event|publish|confirm|decrement")],
             "explanation": "Validate → _check_stock → _reserve (reserved += qty) → _total → charge with retries. "
                            "On PaymentFailed it releases the reservation and publishes order.failed; otherwise it "
                            "moves reserved quantity out of stock, marks the order confirmed and publishes order.confirmed."},
            {"id": "bugs", "kind": "lines",
             "prompt": "Click every line that contains a bug, code smell or performance issue (aim for 8).",
             "explanation": "Planted issues: float money, O(n) repo lookup, off-by-one stock check, stale cache after "
                            "reservation, missing idempotency key, retrying non-retryable declines, mutable default "
                            "argument, and a check-then-act race between _check_stock and _reserve."},
            {"id": "trace", "kind": "choice",
             "prompt": "Product A has stock=3, reserved=0. A user orders exactly 3 units. What happens?",
             "options": ["Order confirmed, stock becomes 0", "OutOfStock is raised", "ValueError is raised",
                         "Order confirmed, but stock becomes -3"],
             "answer": 1,
             "explanation": "available (3) > qty (3) is False, so the off-by-one check raises OutOfStock for a valid order."},
            {"id": "complexity", "kind": "text",
             "prompt": "What is the time complexity of reserve_order for n order items and m products? How would you improve it?",
             "rubric": [("Identifies O(n·m) because of the linear find()", r"n\s*[\*x×·]\s*m|n\s*m\b|o\(nm\)|linear"),
                        ("Proposes a dict / hash index by sku", r"dict|hash|map|index"),
                        ("States the improved O(n)", r"o\(n\)")],
             "explanation": "Each find() is O(m) and is called several times per item → O(n·m). Index products in a "
                            "dict keyed by sku to make lookups O(1) and the whole call O(n)."},
            {"id": "improve", "kind": "text", "prompt": "List the top improvements you would ship, most important first.",
             "rubric": [("Idempotency key for payments", r"idempot"),
                        ("Atomic reservation (lock / transaction / conditional update)", r"lock|atomic|transaction|select .*for update|compare"),
                        ("Invalidate or bypass cache on writes", r"invalidat|cache"),
                        ("Decimal / integer money", r"decimal|cents|paise|integer"),
                        ("Only retry transient errors", r"transient|timeout|only retry|declin|5\d\d")],
             "explanation": "Highest impact first: idempotent payment calls, atomic stock reservation, cache invalidation "
                            "on write, Decimal money, retry only transient errors with jittered backoff, dict index."},
        ],
    },
    {
        "id": "comp-ratelimit", "section": "comprehension", "title": "Express rate-limiter middleware",
        "difficulty": "Medium", "minutes": 20,
        "summary": "A sliding-window limiter guarding a public API. Find the security, memory and logic flaws.",
        "context": "After launch the API pods slowly run out of memory, and a scraper is still getting through.",
        "files": [("rateLimit.js", "javascript", RATE_LIMITER)],
        "tasks": [
            {"id": "explain", "kind": "text", "prompt": "Explain how a request flows through rateLimit().",
             "rubric": [("Identifies the client", r"client|ip|identif"),
                        ("Prunes timestamps older than the window", r"prun|old|window|expire"),
                        ("Rejects with 429 + Retry-After when over the limit", r"429|retry"),
                        ("Records the timestamp and calls next()", r"push|record|next")],
             "explanation": "Resolve client id → fetch/create its timestamp list → drop entries older than 60s → "
                            "if over the limit return 429 with Retry-After → otherwise push now, set remaining header, next()."},
            {"id": "bugs", "kind": "lines", "prompt": "Flag the lines with bugs or risks (5).",
             "explanation": "Spoofable X-Forwarded-For, O(n) shift, shared bucket / exact-path route limits, "
                            "never-evicted map keys (memory leak), and an off-by-one that allows limit+1 requests."},
            {"id": "fix", "kind": "text", "prompt": "How would you make this production-ready across 20 pods?",
             "rubric": [("Shared store such as Redis", r"redis|shared|central|memcache"),
                        ("Atomic ops / Lua / sorted set / token bucket", r"atomic|lua|zset|sorted set|token bucket|incr"),
                        ("TTL / eviction", r"ttl|expir|evict"),
                        ("Trust proxy configuration for client IP", r"trust ?proxy|proxy|real ip")],
             "explanation": "Move state to Redis (sorted set or INCR+EXPIRE / token bucket via Lua for atomicity), "
                            "set TTLs so idle keys disappear, and derive client IP using trusted-proxy config."},
        ],
    },
    # ------------------------------------------------------------------ 2. AI-Assisted Coding
    {
        "id": "ai-topk", "section": "ai_assist", "title": "Top K Frequent Elements — validate the AI",
        "difficulty": "Medium", "minutes": 15,
        "summary": "Use the AI's answer, then prove (or disprove) it.",
        "context": "Problem: given an integer array nums and an integer k, return the k most frequent elements. "
                   "You may use the AI-generated answer — but you must defend it in the interview.",
        "files": [_ai_file('''from collections import Counter


def top_k_frequent(nums: list[int], k: int) -> list[int]:
    counts = Counter(nums)
    buckets = [[] for _ in range(len(nums) + 1)]
    for num, freq in counts.items():
        buckets[freq].append(num)

    result = []
    for freq in range(len(buckets) - 1, 0, -1):
        for num in buckets[freq]:
            result.append(num)
            if len(result) == k:
                return result
    return result
''')],
        "tasks": [
            {"id": "correct", "kind": "text", "prompt": "Why is this solution correct?",
             "rubric": [("Counts frequencies", r"count|frequenc"),
                        ("Bucket index = frequency, max frequency ≤ n", r"bucket|index.*freq|≤ ?n|<= ?n|at most n"),
                        ("Scans from highest frequency down and stops at k", r"high|descend|reverse|down|stop")],
             "explanation": "Counter gives each value's frequency; frequency is at most n so it can index a bucket. "
                            "Walking buckets from high to low yields elements in non-increasing frequency, stopping at k."},
            {"id": "edges", "kind": "text", "prompt": "What edge cases exist?",
             "rubric": [("Ties in frequency", r"tie|same freq|equal"),
                        ("k equals number of distinct values", r"distinct|unique|k ?= ?|all element"),
                        ("Negative numbers / duplicates", r"negativ|duplicat"),
                        ("Single element / empty input", r"single|one element|empty")],
             "explanation": "Ties (order among equal frequencies is arbitrary), k == distinct count, negative values "
                            "(fine — they're keys, not indices), single element, empty input when k=0."},
            {"id": "tradeoffs", "kind": "text", "prompt": "What are the trade-offs versus a heap-based solution?",
             "rubric": [("Bucket sort O(n) time", r"o\(n\)"),
                        ("Heap O(n log k)", r"log ?k|heap"),
                        ("Bucket uses O(n) extra memory / heap better for streams", r"memory|space|stream")],
             "explanation": "Buckets: O(n) time but O(n) extra space and needs all data up front. Heap: O(n log k) "
                            "time, O(k) extra space, works on streams."},
            {"id": "fail", "kind": "choice", "prompt": "Can this AI solution fail?",
             "options": ["Yes — negative numbers crash it", "Yes — it returns duplicates",
                         "No for valid input; with k > distinct values it silently returns fewer than k",
                         "Yes — it is O(n²)"],
             "answer": 2,
             "explanation": "It's correct for valid inputs. If k exceeds the number of distinct values it returns fewer "
                            "items without error — a contract question worth raising in the interview."},
        ],
    },
    {
        "id": "ai-intervals", "section": "ai_assist", "title": "Merge Intervals — trust but verify",
        "difficulty": "Medium", "minutes": 15,
        "summary": "The AI's merge looks clean. Is it safe to ship?",
        "context": "Problem: merge all overlapping intervals and return the result. The AI produced this in 3 seconds.",
        "files": [_ai_file('''def merge(intervals: list[list[int]]) -> list[list[int]]:
    intervals.sort(key=lambda x: x[0])
    merged = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
''')],
        "tasks": [
            {"id": "correct", "kind": "text", "prompt": "Why is it correct?",
             "rubric": [("Sorting by start makes overlaps adjacent", r"sort"),
                        ("Compares with the last merged interval", r"last|previous|merged\[-1\]"),
                        ("Extends end with max (handles containment)", r"max|contain|nested")],
             "explanation": "After sorting by start, any interval that overlaps the result must overlap the last merged "
                            "interval; max() handles intervals fully contained in the previous one."},
            {"id": "edges", "kind": "text", "prompt": "Which edge cases would you test?",
             "rubric": [("Touching intervals like [1,2],[2,3]", r"touch|adjacent|\[1, ?2\].*\[2|equal end|<="),
                        ("Nested intervals", r"nest|contain|inside"),
                        ("Empty / single interval", r"empty|single|one interval"),
                        ("Unsorted input", r"unsorted|order")],
             "explanation": "Touching endpoints (merged because of <=), nested, empty list, single interval, unsorted input."},
            {"id": "fail", "kind": "text", "prompt": "Can the AI solution cause problems in production? Trade-offs?",
             "rubric": [("Mutates the caller's list (in-place sort)", r"mutat|in.?place|side.?effect|caller"),
                        ("O(n log n) dominated by sort", r"n ?log ?n"),
                        ("Clarify whether touching intervals should merge", r"touch|spec|requirement|clarif")],
             "explanation": "intervals.sort() mutates the caller's input (and inner lists via merged[-1][1]) — use "
                            "sorted() and copy. O(n log n) time. Confirm with the interviewer whether [1,2],[2,3] should merge."},
        ],
    },
    {
        "id": "ai-lru", "section": "ai_assist", "title": "LRU Cache — defend the AI design",
        "difficulty": "Medium", "minutes": 15,
        "summary": "OrderedDict-based LRU. Explain why it's O(1) and where it breaks.",
        "context": "Design an LRU cache with get/put in O(1). The AI suggested OrderedDict.",
        "files": [_ai_file('''from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.data = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.data:
            return -1
        self.data.move_to_end(key)
        return self.data[key]

    def put(self, key: int, value: int) -> None:
        self.data[key] = value
        self.data.move_to_end(key)
        if len(self.data) > self.capacity:
            self.data.popitem(last=False)
''')],
        "tasks": [
            {"id": "correct", "kind": "text", "prompt": "Why are get and put O(1)?",
             "rubric": [("Hash map lookup", r"hash|dict|map"),
                        ("Doubly linked list ordering", r"linked list|doubly|order"),
                        ("move_to_end / popitem are O(1)", r"move_to_end|popitem|o\(1\)")],
             "explanation": "OrderedDict = hash map + doubly linked list; lookup, move_to_end and popitem(last=False) are O(1)."},
            {"id": "fail", "kind": "text", "prompt": "When can it fail or be the wrong choice?",
             "rubric": [("Not thread-safe", r"thread|concurren|lock"),
                        ("Interviewer may want a hand-built list", r"hand|implement.*list|from scratch|built.?in"),
                        ("Capacity 0 / negative", r"capacity ?(0|zero)|negative")],
             "explanation": "Not thread-safe; capacity 0 inserts then immediately evicts; interviewers often ask you to "
                            "implement the linked list yourself to show you understand it."},
        ],
    },
    # ------------------------------------------------------------------ 3. Debugging Simulator
    {
        "id": "dbg-shared-cart", "section": "debugging", "title": "Users see other people's carts",
        "difficulty": "Medium", "minutes": 20, "summary": "Backend bug — a P1 privacy incident.",
        "context": "INCIDENT P1 — 14:02. Support reports customers seeing items they never added. It started after "
                   "yesterday's 'cart performance' release. Investigate and resolve.",
        "files": [("cart_api.py", "python", '''@router.get("/cart")
async def get_cart(request: Request, user: User = Depends(current_user)):
    key = f"cache:{request.url.path}"
    if cached := await redis.get(key):
        return json.loads(cached)
    cart = await carts.load(user.id)
    await redis.set(key, json.dumps(cart), ex=300)
    return cart
''')],
        "clues": [
            ("Logs", "14:01:55 GET /cart user=812 cache=MISS\\n14:01:57 GET /cart user=455 cache=HIT\\n14:01:58 GET /cart user=91 cache=HIT"),
            ("Redis keys", '> KEYS cache:*\n1) "cache:/cart"'),
            ("Diff of last release", '+ key = f"cache:{request.url.path}"\n+ if cached := await redis.get(key): return json.loads(cached)'),
        ],
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "Root cause?",
             "options": ["Redis eviction policy is LRU", "The cache key doesn't include the user, so all users share one cart entry",
                         "carts.load returns the wrong user", "Session cookies are shared by the CDN"],
             "answer": 1, "explanation": "The key is just the path '/cart' — the first user's cart is served to everyone for 5 minutes."},
            {"id": "fix", "kind": "text", "prompt": "Describe the fix, the immediate mitigation and how you'd prevent recurrence.",
             "rubric": [("Include user id in the cache key", r"user.?id|per.?user|user in.*key"),
                        ("Flush the bad keys / disable cache now", r"flush|delete|purge|disable|rollback|revert"),
                        ("Add a test / review checklist for cache keys", r"test|review|checklist"),
                        ("Invalidate on cart update", r"invalidat|update")],
             "explanation": "Mitigate: roll back or delete cache:/cart. Fix: key = cache:cart:{user.id}, invalidate on "
                            "cart writes. Prevent: tests with two users, review rule that private data caches must be user-scoped."},
        ],
    },
    {
        "id": "dbg-slow-orders", "section": "debugging", "title": "Orders page takes 9 seconds",
        "difficulty": "Medium", "minutes": 20, "summary": "Database query issue under real data volume.",
        "context": "The 'My orders' page was fast in staging but takes ~9 s in production for active users (≈500 orders).",
        "files": [("orders.py", "python", '''def list_orders(db, user_id):
    orders = db.query(Order).filter(Order.user_id == user_id).all()
    return [
        {"id": o.id, "total": o.total, "items": [i.name for i in o.items], "shipping": o.shipment.status}
        for o in orders
    ]
''')],
        "clues": [
            ("Query log", "SELECT * FROM orders WHERE user_id = 812;  -- 1 query\\nSELECT * FROM order_items WHERE order_id = ?;  -- 500 queries\\nSELECT * FROM shipments WHERE order_id = ?;  -- 500 queries"),
            ("EXPLAIN orders", "Seq Scan on orders  (cost=0.00..48211.00 rows=512)\\n  Filter: (user_id = 812)\\n  Rows Removed by Filter: 2,140,331"),
            ("Indexes", "orders: PRIMARY KEY (id)\\norder_items: PRIMARY KEY (id), INDEX (order_id)\\nshipments: PRIMARY KEY (id)"),
        ],
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "What's causing the latency?",
             "options": ["Slow JSON serialisation", "N+1 queries for items and shipments plus a sequential scan on orders.user_id",
                         "The database is out of connections", "Python GIL contention"],
             "answer": 1, "explanation": "1,001 round-trips (N+1) and a full table scan because orders.user_id and shipments.order_id are unindexed."},
            {"id": "fix", "kind": "text", "prompt": "How do you fix it?",
             "rubric": [("Eager-load (joinedload / selectinload / JOIN)", r"eager|joinedload|selectinload|join|prefetch"),
                        ("Index orders.user_id", r"index.*user_id|user_id.*index"),
                        ("Index shipments.order_id", r"shipments?.*index|index.*order_id"),
                        ("Paginate", r"paginat|limit|page")],
             "explanation": "selectinload(Order.items), joinedload(Order.shipment); CREATE INDEX ON orders(user_id) and "
                            "shipments(order_id); paginate the list. Expect ~3 queries and index scans."},
        ],
    },
    {
        "id": "dbg-checkout-504", "section": "debugging", "title": "Intermittent 504s at checkout",
        "difficulty": "Hard", "minutes": 25, "summary": "API failure that cascades during a partner slowdown.",
        "context": "Every evening around 21:00 checkout returns 504 Gateway Timeout for ~10 minutes. The payment "
                   "partner reports 'elevated latency' at the same time.",
        "files": [("payments_client.py", "python", '''session = requests.Session()  # pool size 10


def charge(order):
    for attempt in range(5):
        try:
            return session.post(PARTNER_URL, json=order.payload()).json()
        except requests.RequestException:
            continue
    raise PaymentError("partner unavailable")
''')],
        "clues": [
            ("APM trace", "POST /checkout  60.0s  (gateway timeout)\\n └─ payments_client.charge  59.9s\\n     └─ POST partner/charges  (no response)"),
            ("Thread dump", "worker-1..worker-32: WAITING on HTTPConnectionPool.get_conn (pool exhausted)"),
            ("Partner status", "p99 latency 21:00-21:10: 45s (normally 300ms)"),
        ],
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "Root cause?",
             "options": ["The load balancer timeout is too low", "No request timeout + immediate retries exhaust the pool when the partner slows down",
                         "The partner rejects our TLS certificate", "Python's requests is not thread-safe"],
             "answer": 1, "explanation": "Without a timeout each call waits forever; 5 instant retries multiply load; the 10-connection pool is exhausted and every worker blocks."},
            {"id": "fix", "kind": "text", "prompt": "Propose a resilient design.",
             "rubric": [("Connect/read timeouts", r"timeout"),
                        ("Exponential backoff with jitter", r"backoff|jitter"),
                        ("Circuit breaker / fail fast", r"circuit|fail fast|breaker"),
                        ("Idempotency key on retries", r"idempot"),
                        ("Async / queue payment or bulkhead", r"queue|async|bulkhead|separate pool")],
             "explanation": "Set connect/read timeouts (e.g. 2s/5s), retry only idempotent calls with an idempotency key "
                            "using exponential backoff + jitter, add a circuit breaker, isolate the partner in its own pool "
                            "(bulkhead) or move charging to a queue."},
        ],
    },
    {
        "id": "dbg-coupon-race", "section": "debugging", "title": "Single-use coupon redeemed twice",
        "difficulty": "Medium", "minutes": 15, "summary": "Classic race condition under concurrent requests.",
        "context": "Finance found single-use coupons applied to two orders placed within the same second.",
        "files": [("coupons.py", "python", '''def redeem(db, code, order_id):
    coupon = db.query(Coupon).filter_by(code=code).one()
    if coupon.used:
        raise CouponUsed()
    apply_discount(order_id, coupon)
    coupon.used = True
    db.commit()
''')],
        "clues": [
            ("Logs", "12:00:00.101 redeem code=WELCOME50 order=1001 used=False\\n12:00:00.103 redeem code=WELCOME50 order=1002 used=False"),
            ("Isolation level", "SHOW transaction_isolation; → read committed"),
        ],
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "Root cause?",
             "options": ["Missing database index", "Check-then-act race: both requests read used=False before either commits",
                         "The ORM caches the coupon", "Clock skew between servers"],
             "answer": 1, "explanation": "Two transactions read the same row under READ COMMITTED and both pass the check."},
            {"id": "fix", "kind": "text", "prompt": "Fix it so it is correct under concurrency.",
             "rubric": [("Atomic conditional UPDATE ... WHERE used = false", r"update .*where|conditional update|rowcount|returning"),
                        ("Or row lock SELECT ... FOR UPDATE", r"for update|lock"),
                        ("Unique constraint on redemptions", r"unique"),
                        ("Test with concurrent requests", r"concurren|parallel|load test|test")],
             "explanation": "UPDATE coupons SET used=true WHERE code=:c AND used=false RETURNING id — proceed only if a row "
                            "was updated; or SELECT ... FOR UPDATE; back it with a unique (coupon_id) redemption row and a concurrency test."},
        ],
    },
    {
        "id": "dbg-node-oom", "section": "debugging", "title": "Node service OOMs every 6 hours",
        "difficulty": "Hard", "minutes": 20, "summary": "Memory leak and performance bottleneck.",
        "context": "The notifications service restarts every ~6h with 'JavaScript heap out of memory'. Latency also creeps up before each crash.",
        "files": [("notify.js", "javascript", '''const bus = require("./bus"); // global EventEmitter
const sent = new Map();

app.post("/notify", async (req, res) => {
  const { userId, message } = req.body;
  bus.on("delivered", (evt) => {
    if (evt.userId === userId) res.locals.delivered = true;
  });
  sent.set(`${userId}:${Date.now()}`, message);
  await queue.publish({ userId, message });
  res.json({ queued: true });
});
''')],
        "clues": [
            ("Heap snapshot diff", "+1.2M  (closure) in notify.js:6\\n+410k  Map entries in `sent`"),
            ("Warning log", "MaxListenersExceededWarning: Possible EventEmitter memory leak detected. 11 delivered listeners added."),
            ("Metrics", "event loop lag rises from 2ms to 900ms over 6h; bus 'delivered' emit takes 400ms"),
        ],
        "tasks": [
            {"id": "root", "kind": "choice", "prompt": "Root cause?",
             "options": ["The queue client leaks sockets", "A listener is added to a global emitter per request and the `sent` map grows forever",
                         "Large JSON bodies", "Too many async functions"],
             "answer": 1, "explanation": "Every request adds a listener that is never removed (each 'delivered' emit loops over all of them) and `sent` is unbounded."},
            {"id": "fix", "kind": "text", "prompt": "Fix and verify.",
             "rubric": [("Remove the per-request listener (once/off) or route events by id", r"once|off|removelistener|remove listener|map of callbacks"),
                        ("Bound the map (TTL / LRU / external store)", r"ttl|lru|bound|evict|redis|delete"),
                        ("Verify with heap snapshots / load test", r"heap|snapshot|load test|profil|clinic")],
             "explanation": "Don't subscribe per request (use a single listener keyed by id, or once()+off with a timeout); "
                            "replace `sent` with a bounded LRU/TTL or external store; confirm flat heap with snapshots under load."},
        ],
    },
    # ------------------------------------------------------------------ 4. Production Code Reading
    {
        "id": "repo-react", "section": "repos", "title": "React: TaskBoard app",
        "difficulty": "Easy", "minutes": 20, "summary": "Navigate a 7-file React + TypeScript app and explain its architecture.",
        "context": "Open each file in the tree. Understand where state lives, how auth works and how the API is called.",
        "files": REACT_REPO,
        "tasks": [
            {"id": "token", "kind": "choice", "prompt": "Where is the auth token attached to API requests?",
             "options": ["AuthContext.tsx", "useTasks.ts", "api/client.ts (request)", "main.tsx"], "answer": 2,
             "explanation": "request() sets the Authorization header; the token comes from AuthContext via useTasks."},
            {"id": "flow", "kind": "order", "prompt": "Order what happens when a user ticks a task checkbox.",
             "items": ["TaskItem onChange calls onToggle(task)", "useTasks.toggle optimistically flips `done` in state",
                       "tasksApi.toggle sends PATCH /tasks/:id", "On failure the previous task is restored and an error shown"],
             "explanation": "Optimistic UI: update local state first, then call the API, roll back on error."},
            {"id": "bug", "kind": "text", "prompt": "Find one React bug or anti-pattern and explain the fix.",
             "rubric": [("Array index used as key in TaskList", r"key|index"),
                        ("Use task.id as the key", r"task\.id|t\.id|stable id|unique id")],
             "explanation": "TaskList uses key={i}. With memo'd items, reordering/inserting causes wrong reuse. Use key={t.id}."},
            {"id": "arch", "kind": "text", "prompt": "Describe the architecture in 3-4 sentences (layers and responsibilities).",
             "rubric": [("Context for auth state", r"context|auth"),
                        ("Custom hook owns data fetching/state", r"hook|usetasks"),
                        ("API client layer", r"client|api layer|fetch"),
                        ("Presentational components", r"component|presentation|ui")],
             "explanation": "AuthContext holds session state; useTasks is the data layer (fetching, optimistic updates); "
                            "api/client centralises HTTP + auth headers; TaskList/TaskItem are presentational."},
        ],
    },
    {
        "id": "repo-fastapi", "section": "repos", "title": "FastAPI: Bookstore API",
        "difficulty": "Medium", "minutes": 20, "summary": "Router → service → repository layering with SQLAlchemy.",
        "context": "This is a layered FastAPI service. Trace a request and spot design issues.",
        "files": FASTAPI_REPO,
        "tasks": [
            {"id": "flow", "kind": "order", "prompt": "Order the steps for POST /api/books.",
             "items": ["Pydantic validates the body as BookIn", "get_service builds BookService with a request-scoped Session",
                       "BookService.create checks ISBN uniqueness via the repository", "Repository adds the Book and flushes",
                       "Service commits and maps to BookOut"],
             "explanation": "Validation happens before your code runs; DI wires a per-request session; service owns business rules and the transaction."},
            {"id": "layer", "kind": "text", "prompt": "Which layering rule does routers/books.py break, and why does it matter?",
             "rubric": [("get_book reaches into svc.repo directly", r"svc\.repo|repo directly|bypass|get_book"),
                        ("Business logic should stay in the service", r"service"),
                        ("Harder to test / change / enforce rules", r"test|coupl|maintain|change")],
             "explanation": "get_book calls svc.repo.get() — the router bypasses the service layer, coupling HTTP to persistence."},
            {"id": "race", "kind": "text", "prompt": "Two requests create the same ISBN at once. What happens and how do you handle it?",
             "rubric": [("Both pass the by_isbn check", r"both|race|concurren"),
                        ("Unique index makes the second commit fail with IntegrityError", r"unique|integrity"),
                        ("Catch IntegrityError and return 409", r"409|catch|handle")],
             "explanation": "Both checks pass; the DB unique index rejects the second commit with IntegrityError → currently a 500. Catch it and return 409."},
        ],
    },
    {
        "id": "repo-spring", "section": "repos", "title": "Spring Boot: Payments service",
        "difficulty": "Hard", "minutes": 25, "summary": "Controller → service → JPA with an external gateway call.",
        "context": "Read the payments service. Focus on transactions, idempotency and failure handling.",
        "files": SPRING_REPO,
        "tasks": [
            {"id": "idem", "kind": "choice", "prompt": "How is idempotency implemented?",
             "options": ["Only via the gateway header", "Idempotency-Key header → lookup by key + unique constraint, and the key is forwarded to the gateway",
                         "A Redis lock", "It isn't"], "answer": 1,
             "explanation": "findByIdempotencyKey returns the earlier result; the unique constraint guards races; the gateway also receives the key."},
            {"id": "tx", "kind": "text", "prompt": "What's risky about calling the gateway inside @Transactional pay()?",
             "rubric": [("Holds a DB connection/transaction during a remote call", r"connection|hold|long.?running|remote|network"),
                        ("Charge may succeed but the commit fails (inconsistent state)", r"commit fail|inconsisten|rollback|lost|charged"),
                        ("Split into steps / outbox / save PENDING first", r"outbox|separate|pending|two step|saga|split")],
             "explanation": "A slow gateway pins one of 20 Hikari connections; if the commit fails after a successful charge "
                            "you lose the record. Persist PENDING in its own transaction, call the gateway outside it, then update."},
            {"id": "flow", "kind": "order", "prompt": "Order the request flow for POST /api/payments.",
             "items": ["Bean Validation checks PayRequest", "PaymentController calls PaymentService.pay",
                       "Lookup by idempotency key", "Save PENDING payment", "Call gateway with the key",
                       "Mark SUCCEEDED/FAILED; controller returns 201 or 402"],
             "explanation": "Validation → controller → service (idempotency check → persist → external call → state change) → response mapping."},
        ],
    },
]
