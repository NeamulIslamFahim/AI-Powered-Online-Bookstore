import api from "./client";

export const fetchBooksRequest = (params) => {
  const sanitizedParams = Object.fromEntries(
    Object.entries(params || {}).filter(([, value]) => value !== "" && value !== null && value !== undefined)
  );

  return api.get("/books", { params: sanitizedParams });
};
export const fetchBookDetailsRequest = (id) => api.get(`/books/${id}`);
export const createBookRequest = (payload) => api.post("/books", payload);
export const updateBookRequest = (id, payload) => api.put(`/books/${id}`, payload);
export const deleteBookRequest = (id) => api.delete(`/books/${id}`);
export const fetchCategoriesRequest = () => api.get("/categories");
