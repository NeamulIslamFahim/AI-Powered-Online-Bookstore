export default function Footer() {
  return (
    <footer className="mt-16 bg-[#15110d] text-white">
      <div className="mx-auto grid w-[min(1180px,calc(100%-32px))] gap-10 py-12 md:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-amber-300">Online Bookstore</p>
          <h3 className="mt-4 font-display text-5xl">Stories, learning, and checkout in one place.</h3>
          <p className="mt-4 max-w-xl text-sm leading-7 text-white/70">
            Browse books, manage your cart, save favorites, write reviews, and complete orders in
            a modern bookstore experience.
          </p>
        </div>
        <div className="grid gap-8 sm:grid-cols-2">
          <div className="space-y-3">
            <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-300">Explore</h4>
            <a href="/" className="block text-white/80 hover:text-white">
              Home
            </a>
            <a href="/wishlist" className="block text-white/80 hover:text-white">
              Wishlist
            </a>
            <a href="/orders" className="block text-white/80 hover:text-white">
              Orders
            </a>
          </div>
          <div className="space-y-3">
            <h4 className="text-sm font-semibold uppercase tracking-[0.2em] text-amber-300">Legal</h4>
            <p className="text-white/80">All rights reserved by Neamul Islam Fahim</p>
          </div>
        </div>
      </div>
    </footer>
  );
}

