import { configureStore } from "@reduxjs/toolkit";
import authReducer from "../features/auth/authSlice";
import booksReducer from "../features/books/bookSlice";
import cartReducer from "../features/cart/cartSlice";
import ordersReducer from "../features/orders/orderSlice";
import wishlistReducer from "../features/wishlist/wishlistSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    books: booksReducer,
    cart: cartReducer,
    orders: ordersReducer,
    wishlist: wishlistReducer,
  },
});
