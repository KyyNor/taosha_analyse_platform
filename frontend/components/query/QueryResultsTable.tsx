type Props = {
  data: Array<Record<string, any>>;
  generatedSQL?: string;
  loading?: boolean;
};

export default function QueryResultsTable({ data = [], generatedSQL, loading }: Props) {
  if (loading) {
    return <div className="text-sm text-muted-foreground">正在执行查询...</div>;
  }
  if (!data.length) {
    return <div className="text-sm text-muted-foreground">暂无数据</div>;
  }
  const columns = Object.keys(data[0] ?? {});
  return (
    <div className="overflow-auto">
      {generatedSQL ? (
        <pre className="mb-4 rounded-md border bg-muted/30 p-3 text-xs whitespace-pre-wrap">{generatedSQL}</pre>
      ) : null}
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b">
            {columns.map((c) => (
              <th key={c} className="px-3 py-2 text-left font-medium text-muted-foreground">{c}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={i} className="border-b">
              {columns.map((c) => (
                <td key={c} className="px-3 py-2">{String(row[c])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}