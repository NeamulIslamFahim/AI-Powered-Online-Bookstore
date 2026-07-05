export default function RatingStars({ rating = 0 }) {
  return (
    <div className="flex items-center gap-1 text-amber-500">
      {Array.from({ length: 5 }).map((_, index) => (
        <span key={index}>{index < Math.round(rating) ? "★" : "☆"}</span>
      ))}
    </div>
  );
}

