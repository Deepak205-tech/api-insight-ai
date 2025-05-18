export function Label({ htmlFor, children, className = "" }) {
  return (
    <label
      htmlFor={htmlFor}
      className={`block mb-1 font-medium text-gray-700 ${className}`}
    >
      {children}
    </label>
  );
}
