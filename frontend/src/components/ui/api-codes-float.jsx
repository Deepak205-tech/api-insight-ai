// Animated API codes floating towards the user
import { motion, AnimatePresence } from "motion/react";
import { useEffect, useState } from "react";

const API_CODES = [
  "200", "201", "204", "400", "401", "403", "404", "409", "422", "429", "500", "502", "503"
];

function randomBetween(a, b) {
  return Math.random() * (b - a) + a;
}

export function ApiCodesFloat({ count = 12, duration = 3, className = "" }) {
  const [codes, setCodes] = useState([]);

  useEffect(() => {
    // Generate floating codes
    setCodes(
      Array.from({ length: count }).map((_, i) => ({
        code: API_CODES[Math.floor(Math.random() * API_CODES.length)],
        id: `${i}-${Math.random()}`,
        left: randomBetween(5, 95),
        size: randomBetween(1.1, 2.2),
        delay: randomBetween(0, 1.5),
        color: [
          "#22d3ee", // cyan
          "#4ade80", // green
          "#facc15", // yellow
          "#f472b6", // pink
          "#818cf8", // indigo
          "#f87171", // red
        ][Math.floor(Math.random() * 6)]
      }))
    );
  }, [count]);

  return (
    <div className={"pointer-events-none absolute inset-0 z-10 overflow-hidden " + className}>
      <AnimatePresence>
        {codes.map(({ code, id, left, size, delay, color }) => (
          <motion.div
            key={id}
            initial={{ opacity: 0, y: 80, scale: size }}
            animate={{ opacity: 0.85, y: 0, scale: size * 1.1 }}
            exit={{ opacity: 0, y: -80, scale: size * 1.2 }}
            transition={{
              duration: duration + randomBetween(-0.5, 0.5),
              delay,
              ease: "easeInOut"
            }}
            style={{
              position: "absolute",
              left: `${left}%`,
              bottom: 0,
              fontSize: `${size}rem`,
              color,
              fontWeight: 700,
              textShadow: "0 2px 16px rgba(0,0,0,0.25)"
            }}
          >
            {code}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
