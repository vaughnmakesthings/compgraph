import { SkeletonBox } from "@/components/ui/skeleton";

export default function AuthLoading() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading authentication"
      className="flex items-center justify-center"
      style={{ minHeight: "100vh" }}
    >
      <SkeletonBox style={{ width: 360, height: 280 }} />
    </div>
  );
}
