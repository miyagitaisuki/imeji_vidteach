// IMEJI日本語教室 — lấy từ design system của bạn (artifact "IMEJI日本語教室")
export const brand = {
  name: "IMEJI日本語教室",
  color: {
    primary: "#2563eb", primaryDark: "#1d4ed8", primaryLight: "#dbeafe", primary50: "#eff6ff",
    success: "#007a55", warning: "#bb4d00", danger: "#d70037", accent: "#4f39f6",
    text: "#0f172a", textSub: "#526177", border: "#e2e8f0", bg: "#f8fafc", white: "#ffffff",
  },
  font: {
    sans: '"Be Vietnam Pro", "Noto Sans JP", system-ui, sans-serif',
    jp: '"Noto Sans JP", "Be Vietnam Pro", system-ui, sans-serif',
    googleFonts:
      "https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800;900&family=Noto+Sans+JP:wght@400;500;700;900&display=swap",
  },
  radius: { sm: 8, md: 12, lg: 16, xl: 24, full: 9999 },
  shadow: { card: "0 4px 20px -2px rgba(15,23,42,0.04)", pop: "0 25px 50px -12px rgba(15,23,42,0.25)" },
  // Quy tắc: giao diện sáng, chữ trắng chỉ đặt trên primary-600/-700; không vẽ lại logo.
  export: { width: 1920, height: 1080, fps: 30, codec: "h264", loudnessLUFS: -14 },
} as const;
