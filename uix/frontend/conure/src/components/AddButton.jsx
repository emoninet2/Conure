export default function AddButton({ children, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: "6px 12px",
        borderRadius: 6,
        border: "1px solid #2d6cdf",
        background: "#eaf1ff",
        color: "#2d6cdf",
        cursor: "pointer",
        fontWeight: 500,
        display: "inline-flex",
        alignItems: "center",
        gap: 6
      }}
    >
      <span style={{ fontWeight: 700 }}>＋</span>
      {children}
    </button>
  );
}