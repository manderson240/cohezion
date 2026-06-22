import { useState, useEffect } from 'react';

interface VoiceResponse {
  voice: string;
  approval_score: number;
  concerns: string[];
  recommendations: string[];
}

interface QuadratureOutcome {
  approved: boolean;
  consensus_score: number;
  alignment_score: number;
  voice_responses: VoiceResponse[];
  rejection_reason?: string;
}

const VOICE_COLORS: Record<string, { bg: string; border: string; text: string; bar: string }> = {
  Architect: { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-700', bar: 'bg-blue-500' },
  Engineer: { bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-700', bar: 'bg-emerald-500' },
  Ethicist: { bg: 'bg-purple-50', border: 'border-purple-200', text: 'text-purple-700', bar: 'bg-purple-500' },
  Resource: { bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-700', bar: 'bg-amber-500' },
};

function QuadraturePanel({ journeyId }: { journeyId: string }) {
  const [mode, setMode] = useState<'preflight' | 'full'>('preflight');
  const [data, setData] = useState<QuadratureOutcome | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/journey-nexus/quadrature/${journeyId}?mode=${mode}`);
        if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
        const json: QuadratureOutcome = await res.json();
        if (!cancelled) setData(json);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchData();
    return () => { cancelled = true; };
  }, [journeyId, mode]);

  const getVoiceColor = (voice: string) => VOICE_COLORS[voice] || { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-700', bar: 'bg-gray-500' };

  return (
    <div className="w-full max-w-6xl mx-auto p-4 space-y-6">
      {/* Header / Banner */}
      <div className={`rounded-xl border p-6 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4 ${data?.approved ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${data?.approved ? 'bg-green-500' : 'bg-red-500'}`} />
          <h2 className="text-xl font-bold text-gray-900">
            {data?.approved ? 'Quadrature Approved' : 'Quadrature Rejected'}
          </h2>
          {data?.rejection_reason && (
            <span className="text-sm text-red-600 font-medium ml-2">({data.rejection_reason})</span>
          )}
        </div>
        <div className="flex gap-6">
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Consensus</p>
            <p className="text-2xl font-bold text-gray-900">{data ? (data.consensus_score * 100).toFixed(0) : '--'}%</p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wide">Alignment</p>
            <p className="text-2xl font-bold text-gray-900">{data ? (data.alignment_score * 100).toFixed(0) : '--'}%</p>
          </div>
        </div>
      </div>

      {/* Mode Toggle */}
      <div className="flex justify-center">
        <div className="bg-gray-100 p-1 rounded-lg inline-flex">
          <button
            onClick={() => setMode('preflight')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'preflight' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Preflight
          </button>
          <button
            onClick={() => setMode('full')}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${mode === 'full' ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'}`}
          >
            Full Analysis
          </button>
        </div>
      </div>

      {/* Loading / Error States */}
      {loading && (
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-center">
          {error}
        </div>
      )}

      {/* Voice Cards */}
      {!loading && !error && data && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {data.voice_responses.map((voice, idx) => {
            const colors = getVoiceColor(voice.voice);
            return (
              <div key={idx} className={`rounded-xl border ${colors.border} ${colors.bg} p-5 shadow-sm hover:shadow-md transition-shadow`}>
                <div className="flex justify-between items-center mb-4">
                  <h3 className={`text-lg font-bold ${colors.text}`}>{voice.voice}</h3>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-500">Approval</span>
                    <div className="w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${colors.bar}`}
                        style={{ width: `${voice.approval_score * 100}%` }}
                      />
                    </div>
                    <span className="text-sm font-bold text-gray-900">{(voice.approval_score * 100).toFixed(0)}%</span>
                  </div>
                </div>

                <div className="space-y-4">
                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Concerns</h4>
                    {voice.concerns.length > 0 ? (
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        {voice.concerns.map((c, i) => <li key={i}>{c}</li>)}
                      </ul>
                    ) : (
                      <p className="text-sm text-gray-400 italic">No concerns raised.</p>
                    )}
                  </div>

                  <div>
                    <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Recommendations</h4>
                    {voice.recommendations.length > 0 ? (
                      <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                        {voice.recommendations.map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    ) : (
                      <p className="text-sm text-gray-400 italic">No recommendations.</p>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default QuadraturePanel;
