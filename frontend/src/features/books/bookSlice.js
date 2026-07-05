import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  createBookRequest,
  deleteBookRequest,
  fetchBookDetailsRequest,
  fetchBooksRequest,
  fetchCategoriesRequest,
  updateBookRequest,
} from "../../api/booksApi";
import { getApiError } from "../../utils/apiError";

const initialState = {
  books: [],
  categories: [],
  selectedBook: null,
  pagination: { page: 1, limit: 8, total: 0, total_pages: 1 },
  loading: false,
  error: null,
};

export const fetchBooks = createAsyncThunk("books/fetchAll", async (params, { rejectWithValue }) => {
  try {
    const response = await fetchBooksRequest(params);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load books"));
  }
});

export const fetchBookDetails = createAsyncThunk("books/fetchDetails", async (id, { rejectWithValue }) => {
  try {
    const response = await fetchBookDetailsRequest(id);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load book"));
  }
});

export const fetchCategories = createAsyncThunk("books/fetchCategories", async (_, { rejectWithValue }) => {
  try {
    const response = await fetchCategoriesRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load categories"));
  }
});

export const createBook = createAsyncThunk("books/create", async (payload, { rejectWithValue }) => {
  try {
    const response = await createBookRequest(payload);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to create book"));
  }
});

export const updateBook = createAsyncThunk("books/update", async ({ id, payload }, { rejectWithValue }) => {
  try {
    const response = await updateBookRequest(id, payload);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to update book"));
  }
});

export const deleteBook = createAsyncThunk("books/delete", async (id, { rejectWithValue }) => {
  try {
    await deleteBookRequest(id);
    return id;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to delete book"));
  }
});

const bookSlice = createSlice({
  name: "books",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchBooks.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchBooks.fulfilled, (state, action) => {
        state.loading = false;
        state.books = action.payload.items;
        state.pagination = action.payload.pagination;
      })
      .addCase(fetchBooks.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchBookDetails.fulfilled, (state, action) => {
        state.selectedBook = action.payload;
      })
      .addCase(fetchCategories.fulfilled, (state, action) => {
        state.categories = action.payload;
      })
      .addCase(createBook.fulfilled, (state, action) => {
        state.books.unshift(action.payload);
      })
      .addCase(updateBook.fulfilled, (state, action) => {
        state.books = state.books.map((book) => (book.id === action.payload.id ? action.payload : book));
        state.selectedBook = action.payload;
      })
      .addCase(deleteBook.fulfilled, (state, action) => {
        state.books = state.books.filter((book) => book.id !== action.payload);
      });
  },
});

export default bookSlice.reducer;
