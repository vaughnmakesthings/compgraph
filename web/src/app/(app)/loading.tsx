import { SkeletonBox } from "@/components/ui/skeleton";

export default function AppLoading() {
  return (
    <div
      role="status"
      aria-busy="true"
      aria-label="Loading page content"
    >
      <div className="mb-6">
        <SkeletonBox className="h-7 w-48 mb-2" />
        <SkeletonBox className="h-4 w-72" />
      </div>

      <div className="grid grid-cols-4 gap-4 mb-6">
        <SkeletonBox className="h-[96px]" />
        <SkeletonBox className="h-[96px]" />
        <SkeletonBox className="h-[96px]" />
        <SkeletonBox className="h-[96px]" />
      </div>

      <SkeletonBox className="h-[320px]" />
    </div>
  );
}
