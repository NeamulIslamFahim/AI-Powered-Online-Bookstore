const defaultBook = {
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

export default function BookForm({ form = defaultBook, categories = [], onChange, onSubmit, submitLabel }) {
  return (
    <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
      {[
        ["title", "Title"],
        ["author", "Author"],
        ["price", "Price"],
        ["stock_quantity", "Stock Quantity"],
        ["image_url", "Image URL"],
        ["isbn", "ISBN"],
        ["published_date", "Published Date"],
      ].map(([name, label]) => (
        <div key={name}>
          <label className="mb-2 block text-sm font-semibold text-ink/70">{label}</label>
          <input
            className="input"
            type={name === "published_date" ? "date" : name === "price" ? "number" : name === "stock_quantity" ? "number" : "text"}
            step={name === "price" ? "0.01" : undefined}
            min={name === "price" || name === "stock_quantity" ? "0" : undefined}
            name={name}
            value={form[name] || ""}
            onChange={onChange}
          />
        </div>
      ))}

      <div>
        <label className="mb-2 block text-sm font-semibold text-ink/70">Category</label>
        <select className="input" name="category_id" value={form.category_id || ""} onChange={onChange}>
          <option value="">Select category</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </select>
      </div>

      <div className="md:col-span-2">
        <label className="mb-2 block text-sm font-semibold text-ink/70">Description</label>
        <textarea className="input min-h-32" name="description" value={form.description || ""} onChange={onChange} />
      </div>

      <div className="md:col-span-2">
        <button type="submit" className="btn-primary">
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
