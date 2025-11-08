export default function Loading() {
  return (
    <div className="container mx-auto p-8">
      <div className="animate-pulse">
        <div className="h-8 bg-gray-200 rounded w-64 mb-8"></div>
        <div className="grid grid-cols-3 gap-6">
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    </div>
  )
}
