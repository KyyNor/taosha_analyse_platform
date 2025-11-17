"use client";
import { useState } from "react";
import QueryForm from "../../../components/common/QueryForm";
import QueryResultsTable from "../../../components/query/QueryResultsTable";
import QueryProgress from "../../../components/common/QueryProgress";
import Welcome from "../../../components/common/Welcome";
import { runQuery, fetchHistory } from "../../../lib/services/queryService";

export default function Page() {
  const [initialQuery, setInitialQuery] = useState("");
  const [hasActiveQuery, setHasActiveQuery] = useState(false);
  const [isQueryRunning, setIsQueryRunning] = useState(false);
  const [resultData, setResultData] = useState<any[]>([]);
  const [generatedSQL, setGeneratedSQL] = useState<string | undefined>(undefined);

  const handleSubmitQuery = async (payload: { text: string }) => {
    setHasActiveQuery(true);
    setIsQueryRunning(true);
    setResultData([]);
    setGeneratedSQL(undefined);
    try {
      const res = await runQuery({ text: payload.text });
      setResultData(res?.data ?? []);
      setGeneratedSQL(res?.sql);
    } catch (e) {
      // 可进一步接入 toast
    } finally {
      setIsQueryRunning(false);
      setHasActiveQuery(false);
    }
  };

  const handleCancelQuery = () => {
    setIsQueryRunning(false);
    setHasActiveQuery(false);
  };

  const quickExamples = [
    "9月30日所有账户的余额",
    "显示最近一个月的销售数据",
    "查询各产品类别的销售占比",
    "找出注册用户最多的地区",
    "分析订单金额分布情况"
  ];

  const handleExampleClick = (example: string) => {
    setInitialQuery(example);
    setTimeout(() => setInitialQuery(""), 100);
  };

  const handleCopySQL = (sql: string) => {
    navigator.clipboard.writeText(sql);
  };

  const hasResults = resultData.length > 0;

  return (
    <div className="space-y-4">
      <QueryForm initialQuery={initialQuery} onSubmit={handleSubmitQuery} onCancel={handleCancelQuery} />

      <div className="space-y-4">
        {hasResults ? (
          <div className="rounded-md border p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-lg font-semibold">查询结果</h3>
            </div>
            <QueryResultsTable data={resultData} generatedSQL={generatedSQL} loading={isQueryRunning} />
          </div>
        ) : null}

        {!hasResults && !hasActiveQuery ? (
          <Welcome examples={quickExamples} onPick={handleExampleClick} />
        ) : null}

        {hasActiveQuery ? (
          <QueryProgress onCancel={handleCancelQuery} onCopySQL={handleCopySQL} sql={generatedSQL} />
        ) : null}
      </div>
    </div>
  );
}