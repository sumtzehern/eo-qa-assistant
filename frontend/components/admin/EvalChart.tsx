"use client";

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

const MOCK_EVAL_DATA = [
  { date: "Apr 22", groundedness: 0.82, retrieval_relevance: 0.79, overall: 0.81 },
  { date: "Apr 23", groundedness: 0.85, retrieval_relevance: 0.80, overall: 0.83 },
  { date: "Apr 24", groundedness: 0.83, retrieval_relevance: 0.82, overall: 0.82 },
  { date: "Apr 25", groundedness: 0.87, retrieval_relevance: 0.84, overall: 0.86 },
  { date: "Apr 26", groundedness: 0.86, retrieval_relevance: 0.83, overall: 0.85 },
  { date: "Apr 27", groundedness: 0.88, retrieval_relevance: 0.85, overall: 0.87 },
  { date: "Apr 28", groundedness: 0.89, retrieval_relevance: 0.86, overall: 0.87 },
];

export default function EvalChart() {
  const t = useStrings();

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
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={MOCK_EVAL_DATA} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
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
    </div>
  );
}
