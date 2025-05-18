// MagicUI Spinner (Loader) component
import { motion } from "motion/react";

export function Spinner({ size = 48, color = "#22d3ee", className = "" }) {
  return (
    <motion.svg
      className={"animate-spin " + className}
      width={size}
      height={size}
      viewBox="0 0 50 50"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Loading spinner"
    >
      <circle
        cx="25"
        cy="25"
        r="20"
        stroke={color}
        strokeWidth="5"
        opacity="0.2"
      />
      <motion.circle
        cx="25"
        cy="25"
        r="20"
        stroke={color}
        strokeWidth="5"
        strokeDasharray="31.4 94.2"
        strokeLinecap="round"
        initial={{ rotate: 0 }}
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
      />
    </motion.svg>
  );
}
