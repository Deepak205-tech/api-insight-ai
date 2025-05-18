export function Button({ children, onClick, className = "" }) {
  return (
    <button
      onClick={onClick}
      className={`w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 rounded-lg transition ${className}`}
    >
      {children}
    </button>
  );
}
