import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Alert from "../components/Alert";
import BookForm from "../components/BookForm";
import Modal from "../components/Modal";
import { createBook, deleteBook, fetchBooks, fetchCategories, updateBook } from "../features/books/bookSlice";

const emptyForm = {
  title: "",
  author: "",
  description: "",
  price: "",
  stock_quantity: "",
  category_id: "",
  image_url: "",
  isbn: "",
  published_date: "",
};

function toEditableForm(book) {
  return {
    title: book.title || "",
    author: book.author || "",
    description: book.description || "",
    price: book.price ?? "",
    stock_quantity: book.stock_quantity ?? "",
    category_id: book.category_id ?? "",
    image_url: book.image_url || "",
    isbn: book.isbn || "",
    published_date: book.published_date || "",
  };
}

export default function AdminBookManagerPage() {
  const dispatch = useDispatch();
  const { books, categories, error } = useSelector((state) => state.books);
  const [form, setForm] = useState(emptyForm);
  const [editingBook, setEditingBook] = useState(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    dispatch(fetchBooks({ page: 1, limit: 50 }));
    dispatch(fetchCategories());
  }, [dispatch]);

  function handleChange(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const payload = {
      title: form.title.trim(),
      author: form.author.trim(),
      description: form.description.trim() || null,
      price: Number(form.price),
      stock_quantity: Number(form.stock_quantity),
      category_id: Number(form.category_id),
      image_url: form.image_url.trim() || null,
      isbn: form.isbn.trim() || null,
      published_date: form.published_date || null,
    };

    const action = editingBook
      ? await dispatch(updateBook({ id: editingBook.id, payload }))
      : await dispatch(createBook(payload));

    if (action.error) {
      return;
    }

    setForm(emptyForm);
    setEditingBook(null);
    setOpen(false);
  }

  function openCreateModal() {
    setEditingBook(null);
    setForm(emptyForm);
    setOpen(true);
  }

  function openEditModal(book) {
    setEditingBook(book);
    setForm(toEditableForm(book));
    setOpen(true);
  }

  return (
    <div className="space-y-8 py-8">
      <section className="surface p-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-bronze">Admin books</p>
            <h1 className="mt-3 font-display text-5xl">Manage bookstore inventory</h1>
          </div>
          <button type="button" className="btn-primary" onClick={openCreateModal}>
            Add Book
          </button>
        </div>

        <div className="mt-6">
          <Alert message={error} />
        </div>

        <div className="mt-8 space-y-4">
          {!books.length ? <p className="text-sm text-ink/60">No books found in inventory.</p> : null}
          {books.map((book) => (
            <div key={book.id} className="rounded-3xl bg-mist p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <h3 className="font-display text-3xl">{book.title}</h3>
                  <p className="text-sm text-ink/60">
                    {book.author} | Stock {book.stock_quantity} | ${book.price}
                  </p>
                </div>
                <div className="flex gap-3">
                  <button type="button" className="btn-secondary" onClick={() => openEditModal(book)}>
                    Edit
                  </button>
                  <button type="button" className="btn-primary" onClick={() => dispatch(deleteBook(book.id))}>
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <Modal open={open} title={editingBook ? "Edit Book" : "Add Book"} onClose={() => setOpen(false)}>
        <BookForm
          form={form}
          categories={categories}
          onChange={handleChange}
          onSubmit={handleSubmit}
          submitLabel={editingBook ? "Update Book" : "Create Book"}
        />
      </Modal>
    </div>
  );
}
