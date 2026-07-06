import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  addToCartRequest,
  clearCartRequest,
  fetchCartRequest,
  removeCartItemRequest,
  updateCartItemRequest,
} from "../../api/cartApi";
import { getApiError } from "../../utils/apiError";

const initialState = {
  cart: null,
  loading: false,
  error: null,
};

export const fetchCart = createAsyncThunk("cart/fetch", async (_, { rejectWithValue }) => {
  try {
    const response = await fetchCartRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load cart"));
  }
});

export const addToCart = createAsyncThunk("cart/add", async (payload, { rejectWithValue }) => {
  try {
    const response = await addToCartRequest(payload);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to add item"));
  }
});

export const updateCartItem = createAsyncThunk("cart/update", async (payload, { rejectWithValue }) => {
  try {
    const response = await updateCartItemRequest(payload);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to update cart item"));
  }
});

export const removeCartItem = createAsyncThunk("cart/remove", async (bookId, { rejectWithValue }) => {
  try {
    const response = await removeCartItemRequest(bookId);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to remove item"));
  }
});

export const clearCart = createAsyncThunk("cart/clear", async (_, { rejectWithValue }) => {
  try {
    const response = await clearCartRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to clear cart"));
  }
});

const cartSlice = createSlice({
  name: "cart",
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchCart.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchCart.fulfilled, (state, action) => {
        state.loading = false;
        state.cart = action.payload;
        state.error = null;
      })
      .addCase(fetchCart.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(addToCart.fulfilled, (state, action) => {
        state.cart = action.payload;
        state.error = null;
      })
      .addCase(addToCart.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(updateCartItem.fulfilled, (state, action) => {
        state.cart = action.payload;
        state.error = null;
      })
      .addCase(updateCartItem.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(removeCartItem.fulfilled, (state, action) => {
        state.cart = action.payload;
        state.error = null;
      })
      .addCase(removeCartItem.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(clearCart.fulfilled, (state, action) => {
        state.cart = action.payload;
        state.error = null;
      })
      .addCase(clearCart.rejected, (state, action) => {
        state.error = action.payload;
      });
  },
});

export default cartSlice.reducer;
