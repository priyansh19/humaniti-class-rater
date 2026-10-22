/** Re-mounts on every navigation, giving each page a short fade-up (disabled under reduced motion). */
export default function Template({ children }: { children: React.ReactNode }) {
  return <div className="page-enter">{children}</div>;
}
