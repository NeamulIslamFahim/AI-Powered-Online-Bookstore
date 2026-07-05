import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import { addWishlistRequest, fetchWishlistRequest, removeWishlistRequest } from "../../api/wishlistApi";
import { getApiError } from "../../utils/apiError";

const initialState = {
  items: [],
  loading: false,
  error: null,
};

export const fetchWishlist = createAsyncThunk("wishlist/fetch", async (_, { rejectWithValue }) => {
  try {
    const response = await fetchWishlistRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load wishlist"));
  }
});

export const addWishlist = createAsyncThunk("wishlist/add", async (payload, { rejectWithValue }) => {
  try {
    const response = await addWishlistRequest(payload);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to add wishlist item"));
  }
});

export const removeWishlist = createAsyncThunk("wishlist/remove", async (bookId, { rejectWithValue }) => {
  try {
    const response = await removeWishlistRequest(bookId);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to remove wishlist item"));
  }
});

const wishlistSlice = createSlice({
  name: "wishlist",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchWishlist.pending, (state) => {
        state.error = null;
      })
      .addCase(fetchWishlist.fulfilled, (state, action) => {
        state.items = action.payload;
        state.error = null;
      })
      .addCase(fetchWishlist.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(addWishlist.fulfilled, (state, action) => {
        state.items = action.payload;
        state.error = null;
      })
      .addCase(addWishlist.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(removeWishlist.fulfilled, (state, action) => {
        state.items = action.payload;
        state.error = null;
      })
      .addCase(removeWishlist.rejected, (state, action) => {
        state.error = action.payload;
      });
  },
});

export default wishlistSlice.reducer;
