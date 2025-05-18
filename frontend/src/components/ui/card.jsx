export function Card({ children, className = "" }) {
  return (
    <div className={`rounded-xl shadow-lg bg-gradient-to-br from-purple-100 to-pink-50 ${className}`}>
      {children}
    </div>
  );
}

export function CardHeader({ children, className = "" }) {
  return (
    <div className={`p-5 border-b border-purple-300 ${className}`}>
      {children}
    </div>
  );
}

export function CardContent({ children, className = "" }) {
  return (
    <div className={`p-5 ${className}`}>
      {children}
    </div>
  );
}

export function CardFooter({ children, className = "" }) {
  return (
    <div className={`p-5 border-t border-purple-300 flex justify-end space-x-2 ${className}`}>
      {children}
    </div>
  );
}
