"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { useStrings } from "@/lib/i18n";
import { getEvalSummary } from "@/lib/api";

interface ChartPoint {
  date: string;
  groundedness: number;
  retrieval_relevance: number;
  overall: number;
}

export default function EvalChart() {
  const t = useStrings();
  const [data, setData] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getEvalSummary()
      .then((summary) => {
        // Backend returns aggregate stats, not a time series.
        // Build a single chart point from the aggregate values.
        if (
          summary.avg_groundedness !== null ||
          summary.avg_retrieval_relevance !== null ||
          summary.avg_overall_score !== null
        ) {
          setData([
            {
              date: `Last ${summary.period_days}d`,
              groundedness: summary.avg_groundedness ?? 0,
              retrieval_relevance: summary.avg_retrieval_relevance ?? 0,
              overall: summary.avg_overall_score ?? 0,
            },
          ]);
        } else {
          setData([]);
        }
      })
      .catch(() => {
        // Keep empty data on error
        setData([]);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div
      className="rounded-lg p-4"
      style={{
        backgroundColor: "#1C1C1C",
        border: "1px solid #2A2A2A",
      }}
    >
      <h2
        className="text-sm font-semibold uppercase tracking-widest mb-4"
        style={{ color: "#94A3B8" }}
      >
        {t.sevenDayTrend}
      </h2>
      {loading ? (
        <div
          className="flex items-center justify-center"
          style={{ height: 220, color: "#94A3B8", fontSize: 12 }}
        >
          Loading...
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2A2A2A" />
            <XAxis
              dataKey="date"
              tick={{ fill: "#94A3B8", fontSize: 11 }}
              axisLine={{ stroke: "#2A2A2A" }}
              tickLine={false}
            />
            <YAxis
              domain={[0.7, 1.0]}
              tick={{ fill: "#94A3B8", fontSize: 11 }}
              axisLine={{ stroke: "#2A2A2A" }}
              tickLine={false}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1C1C1C",
                border: "1px solid #2A2A2A",
                borderRadius: "6px",
                color: "#ffffff",
                fontSize: "12px",
              }}
              labelStyle={{ color: "#94A3B8" }}
            />
            <Legend
              wrapperStyle={{ color: "#94A3B8", fontSize: "11px", paddingTop: "12px" }}
            />
            <Line
              type="monotone"
              dataKey="groundedness"
              name={t.groundedness}
              stroke="#6EE7B7"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="retrieval_relevance"
              name={t.retrievalRelevance}
              stroke="#60A5FA"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
            <Line
              type="monotone"
              dataKey="overall"
              name={t.overall}
              stroke="#F59E0B"
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
