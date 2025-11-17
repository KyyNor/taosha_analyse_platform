import { Button } from "../ui/button";

type Props = {
  examples: string[];
  onPick: (example: string) => void;
};

export default function Welcome({ examples, onPick }: Props) {
  return (
    <div className="rounded-md border p-8 text-center">
      <h3 className="text-lg font-semibold mb-2">开始您的数据探索之旅</h3>
      <p className="text-muted-foreground mb-6">使用自然语言描述您的查询需求，AI 将为您生成相应的 SQL 并执行分析。</p>
      <div className="flex flex-wrap gap-2 justify-center">
        {examples.map((e) => (
          <Button key={e} variant="outline" size="sm" onClick={() => onPick(e)}>{e}</Button>
        ))}
      </div>
    </div>
  );
}