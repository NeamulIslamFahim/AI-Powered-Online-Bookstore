import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import {
  checkoutRequest,
  fetchAdminOrdersRequest,
  fetchAdminStatsRequest,
  fetchMyOrdersRequest,
  fetchOrderDetailsRequest,
  updateOrderStatusRequest,
} from "../../api/ordersApi";
import { getApiError } from "../../utils/apiError";

const initialState = {
  orders: [],
  selectedOrder: null,
  adminOrders: [],
  stats: null,
  loading: false,
  error: null,
};

export const checkout = createAsyncThunk("orders/checkout", async (_, { rejectWithValue }) => {
  try {
    const response = await checkoutRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Checkout failed"));
  }
});

export const fetchMyOrders = createAsyncThunk("orders/my", async (_, { rejectWithValue }) => {
  try {
    const response = await fetchMyOrdersRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load orders"));
  }
});

export const fetchOrderDetails = createAsyncThunk("orders/details", async (id, { rejectWithValue }) => {
  try {
    const response = await fetchOrderDetailsRequest(id);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load order"));
  }
});

export const fetchAdminOrders = createAsyncThunk("orders/admin", async (_, { rejectWithValue }) => {
  try {
    const response = await fetchAdminOrdersRequest();
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load admin orders"));
  }
});

export const updateOrderStatus = createAsyncThunk(
  "orders/updateStatus",
  async ({ id, status }, { rejectWithValue }) => {
    try {
      const response = await updateOrderStatusRequest(id, status);
      return response.data;
    } catch (error) {
      return rejectWithValue(getApiError(error, "Failed to update order status"));
    }
  }
);

export const fetchAdminStats = createAsyncThunk("orders/stats", async (params, { rejectWithValue }) => {
  try {
    const response = await fetchAdminStatsRequest(params);
    return response.data;
  } catch (error) {
    return rejectWithValue(getApiError(error, "Failed to load dashboard stats"));
  }
});

const orderSlice = createSlice({
  name: "orders",
  initialState,
  reducers: {
    upsertOrder(state, action) {
      const incoming = action.payload;
      const existingIndex = state.orders.findIndex((order) => order.id === incoming.id);
      if (existingIndex >= 0) {
        state.orders[existingIndex] = incoming;
      } else {
        state.orders.unshift(incoming);
      }
      state.selectedOrder = incoming;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(checkout.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(checkout.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedOrder = action.payload;
      })
      .addCase(checkout.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchMyOrders.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchMyOrders.fulfilled, (state, action) => {
        state.loading = false;
        state.orders = action.payload;
      })
      .addCase(fetchMyOrders.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchOrderDetails.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchOrderDetails.fulfilled, (state, action) => {
        state.loading = false;
        state.selectedOrder = action.payload;
      })
      .addCase(fetchOrderDetails.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(fetchAdminOrders.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAdminOrders.fulfilled, (state, action) => {
        state.loading = false;
        state.adminOrders = action.payload;
      })
      .addCase(fetchAdminOrders.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(updateOrderStatus.pending, (state) => {
        state.error = null;
      })
      .addCase(updateOrderStatus.fulfilled, (state, action) => {
        state.adminOrders = state.adminOrders.map((order) =>
          order.id === action.payload.id ? action.payload : order
        );
      })
      .addCase(updateOrderStatus.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(fetchAdminStats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAdminStats.fulfilled, (state, action) => {
        state.loading = false;
        state.stats = action.payload;
      })
      .addCase(fetchAdminStats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      });
  },
});

export const { upsertOrder } = orderSlice.actions;
export default orderSlice.reducer;
