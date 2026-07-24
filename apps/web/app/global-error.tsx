"use client";
export default function GlobalError() {
  return (
    <html lang="en">
      <body style={{ background: "#000", color: "#fff", fontFamily: "system-ui", display: "flex", justifyContent: "center", alignItems: "center", minHeight: "100vh" }}>
        <div style={{ textAlign: "center" }}>
          <h1 style={{ fontSize: "3rem", margin: "0" }}>500</h1>
          <p>Something went wrong</p>
          <a href="/dashboard" style={{ color: "#4A9B70" }}>Go to dashboard</a>
        </div>
      </body>
    </html>
  );
}
