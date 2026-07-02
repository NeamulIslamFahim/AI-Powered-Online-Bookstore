import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import AppRoutes from "./routes/AppRoutes";
import { fetchCurrentUser } from "./features/auth/authSlice";
import { fetchCart } from "./features/cart/cartSlice";
import { fetchWishlist } from "./features/wishlist/wishlistSlice";
import BookstoreAssistantWidget from "./components/BookstoreAssistantWidget";
import AdminChatbotWidget from "./components/AdminChatbotWidget";

export default function App() {
  const dispatch = useDispatch();
  const { token, user } = useSelector((state) => state.auth);
  const [assistantSignal, setAssistantSignal] = useState(0);
  const [selectedBook, setSelectedBook] = useState(null);

  useEffect(() => {
    if (!token) return;
    if (!user) {
      dispatch(fetchCurrentUser());
    }
  }, [dispatch, token, user]);

  useEffect(() => {
    if (!token || !user) return;
    dispatch(fetchCart());
    dispatch(fetchWishlist());
  }, [dispatch, token, user]);

  return (
    <div className="min-h-screen">
      <Navbar onOpenAssistant={() => setAssistantSignal(Date.now())} />
      <main className="mx-auto w-[min(1180px,calc(100%-32px))]">
        <AppRoutes
          onOpenAssistant={() => setAssistantSignal(Date.now())}
          onSelectBook={(book) => setSelectedBook({ ...book, id: `${book.id}-${Date.now()}` })}
        />
      </main>
      <Footer />
      {user?.role === "admin"
        ? <AdminChatbotWidget />
        : <BookstoreAssistantWidget openSignal={assistantSignal} selectedBook={selectedBook} />
      }
    </div>
  );
}
