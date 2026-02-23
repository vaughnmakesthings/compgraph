export function MockupBanner() {
  return (
    <div
      style={{
        borderTop: "2px solid #DCB256",
        border: "1px solid #DCB25640",
        borderTopWidth: "2px",
        borderTopColor: "#DCB256",
        backgroundColor: "#DCB2560D",
        borderRadius: "var(--radius-lg, 8px)",
        padding: "12px 16px",
        marginBottom: "24px",
        display: "flex",
        alignItems: "center",
        gap: "12px",
        fontFamily: "var(--font-body, 'DM Sans Variable', sans-serif)",
      }}
    >
      <span
        style={{
          display: "inline-block",
          backgroundColor: "#DCB2561A",
          color: "#A07D28",
          border: "1px solid #DCB25640",
          borderRadius: "var(--radius-sm, 4px)",
          fontSize: "10px",
          fontWeight: 700,
          letterSpacing: "0.06em",
          textTransform: "uppercase",
          padding: "3px 8px",
          whiteSpace: "nowrap",
          flexShrink: 0,
        }}
      >
        Mockup
      </span>
      <span
        style={{
          fontSize: "13px",
          color: "#2D3142",
          lineHeight: "1.5",
        }}
      >
        This section contains placeholder data for design review. It does not reflect live system data.
      </span>
    </div>
  );
}
