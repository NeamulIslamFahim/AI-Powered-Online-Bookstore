import { Routes, Route } from "react-router-dom";
import HomePage from "../pages/HomePage";
import BookDetailsPage from "../pages/BookDetailsPage";
import BooksPage from "../pages/BooksPage";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import CartPage from "../pages/CartPage";
import CheckoutPage from "../pages/CheckoutPage";
import OrdersPage from "../pages/OrdersPage";
import ProfilePage from "../pages/ProfilePage";
import WishlistPage from "../pages/WishlistPage";
import AdminDashboardPage from "../pages/AdminDashboardPage";
import AdminBookManagerPage from "../pages/AdminBookManagerPage";
import ProtectedRoute from "../components/ProtectedRoute";

export default function AppRoutes({ onOpenAssistant, onSelectBook }) {
  return (
    <Routes>
      <Route path="/" element={<HomePage onOpenAssistant={onOpenAssistant} onSelectBook={onSelectBook} />} />
      <Route path="/books" element={<BooksPage onOpenAssistant={onOpenAssistant} onSelectBook={onSelectBook} />} />
      <Route path="/books/:id" element={<BookDetailsPage onOpenAssistant={onOpenAssistant} onSelectBook={onSelectBook} />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/cart" element={<CartPage />} />
        <Route path="/checkout" element={<CheckoutPage />} />
        <Route path="/orders" element={<OrdersPage />} />
        <Route path="/wishlist" element={<WishlistPage onOpenAssistant={onOpenAssistant} onSelectBook={onSelectBook} />} />
      </Route>
      <Route element={<ProtectedRoute allowedRoles={["admin"]} />}>
        <Route path="/admin" element={<AdminDashboardPage />} />
        <Route path="/admin/books" element={<AdminBookManagerPage />} />
      </Route>
    </Routes>
  );
}
