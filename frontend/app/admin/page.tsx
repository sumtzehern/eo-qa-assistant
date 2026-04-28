import MetricCard from "@/components/admin/MetricCard";
import EvalChart from "@/components/admin/EvalChart";
import FlaggedTable from "@/components/admin/FlaggedTable";
import SourceHealthCard from "@/components/admin/SourceHealthCard";

export default function AdminPage() {
  return (
    <div className="max-w-7xl mx-auto px-6 py-8">
      <h1 className="text-xl font-semibold text-white mb-6">Admin Dashboard</h1>

      {/* Metric Cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <MetricCard
          label="Overall Score"
          value="0.87"
          delta={2.3}
          deltaPositive={true}
          icon="📊"
        />
        <MetricCard
          label="Hallucination Rate"
          value="3.2%"
          delta={-0.8}
          deltaPositive={true}
          icon="⚠️"
        />
        <MetricCard
          label="No-Answer Rate"
          value="8.1%"
          delta={1.2}
          deltaPositive={false}
          icon="❓"
        />
        <MetricCard
          label="Cache Hit Rate"
          value="42%"
          delta={5.0}
          deltaPositive={true}
          icon="⚡"
        />
      </div>

      {/* Eval Chart */}
      <div className="mb-8">
        <EvalChart />
      </div>

      {/* Flagged Queries Table */}
      <div className="mb-8">
        <h2 className="text-sm font-semibold text-enterprise-secondary uppercase tracking-widest mb-4">
          Flagged Queries
        </h2>
        <FlaggedTable />
      </div>

      {/* Source Health */}
      <div>
        <h2 className="text-sm font-semibold text-enterprise-secondary uppercase tracking-widest mb-4">
          Source Health
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <SourceHealthCard />
        </div>
      </div>
    </div>
  );
}
