// Utility: cn (classNames) for MagicUI components
export function cn(...args) {
  return args.filter(Boolean).join(' ');
}
export default cn;
