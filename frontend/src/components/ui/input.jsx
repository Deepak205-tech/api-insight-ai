export function Input({ value, onChange, placeholder, className = "" }) {
  return (
    <input
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      className={`w-full p-3 border-2 border-indigo-400 rounded-lg focus:ring-2 focus:ring-indigo-300 outline-none text-gray-700 ${className}`}
    />
  );
}
