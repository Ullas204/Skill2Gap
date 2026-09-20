interface InfoRowProps {
  items: Array<{ label: string; value: string | number }>;
}

export function InfoRow({ items }: InfoRowProps) {
  return (
    <div className="space-y-3 text-sm">
      {items.map((item) => (
        <div key={item.label} className="flex justify-between">
          <span className="text-gray-500">{item.label}</span>
          <span className="font-medium text-gray-900">{item.value}</span>
        </div>
      ))}
    </div>
  );
}
