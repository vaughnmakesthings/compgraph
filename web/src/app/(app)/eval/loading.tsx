import { SkeletonBox } from "@/components/ui/skeleton";

export default function EvalLoading() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading evaluation data"
    >
      <div className="mb-6">
        <SkeletonBox className="h-7 w-40 mb-2" />
        <SkeletonBox className="h-4 w-64" />
      </div>

      <SkeletonBox className="h-[400px]" />
    </div>
  );
}
