'use client';

import { useState, useEffect, type ChangeEvent } from 'react';
import { EVOField } from '@/components/nexus/EVOField';
import QuadraturePanel from '@/components/nexus/QuadraturePanel';
import NarratePanel from '@/components/nexus/NarratePanel';
import AskOmni from '@/components/nexus/AskOmni';
import useEVOStream from '@/hooks/useEVOStream';

/**
 * Shape of the journey summary returned by `/api/journeys` (via the
 * `journey_loader.summarize()` service). Matches `summarize()` in
 * `src/cohezion/api/services/journey_loader.py`.
 */
interface JourneySummary {
  id: string;
  agent_name?: string;
  intent?: string;
  status?: string;
  final_coherence?: number;
  final_phi_score?: number;
  trajectory_length?: number;
}

const TABS = [
  { id: 'evo', label: 'EVO Stream' },
  { id: 'flume', label: 'FLUME Field' },
  { id: 'quadrature', label: 'Quadrature' },
  { id: 'narrate', label: 'Narrate' },
  { id: 'ask', label: 'Ask' },
] as const;
type TabId = (typeof TABS)[number]['id'];

export default function JourneyNexusPage() {
  const [journeys, setJourneys] = useState<JourneySummary[]>([]);
  const [selectedJourneyId, setSelectedJourneyId] = useState<string>('');
  const [activeTab, setActiveTab] = useState<TabId>('evo');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJourneys = async () => {
      try {
        setLoading(true);
        const res = await fetch('/api/journeys');
        if (!res.ok) throw new Error(`Failed to fetch journeys: ${res.status}`);
        const data: JourneySummary[] = await res.json();
        setJourneys(data);
        if (data.length > 0 && !selectedJourneyId) {
          setSelectedJourneyId(data[0].id);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchJourneys();
  }, [selectedJourneyId]);

  const handleJourneyChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setSelectedJourneyId(e.target.value);
  };

  // Live EVO stream for the selected journey (and only that journey).
  const { events, connected, error: streamError } = useEVOStream(selectedJourneyId);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen w-full bg-slate-950 text-slate-200">
        Loading Nexus...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen w-full bg-slate-950 text-slate-200">
        <div className="rounded-md border border-red-700 bg-red-50 p-4 text-red-700">
          Error: {error}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-full bg-slate-950 text-slate-200 font-sans">
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/50 backdrop-blur-sm">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold tracking-tight text-slate-100">Journey Nexus</h1>
          <div className="flex items-center gap-3">
            <select
              value={selectedJourneyId}
              onChange={handleJourneyChange}
              className="appearance-none bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-72 p-2.5"
            >
              {journeys.length === 0 && <option value="">No journeys available</option>}
              {journeys.map((journey) => (
                <option key={journey.id} value={journey.id}>
                  {journey.agent_name ?? journey.id}
                </option>
              ))}
            </select>
            <span
              className={`text-xs ${connected ? 'text-emerald-400' : 'text-slate-500'}`}
              title={streamError ?? (connected ? 'EVO stream live' : 'EVO stream offline')}
            >
              {connected ? '● live' : '○ offline'}
            </span>
          </div>
        </div>
      </header>

      <nav className="flex items-center px-6 border-b border-slate-800 bg-slate-900/30">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors duration-200 ${
              activeTab === tab.id
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-600'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <main className="flex-1 overflow-auto p-6 bg-slate-950">
        <div className="h-full w-full">
          {selectedJourneyId === '' && (
            <div className="text-slate-500 text-sm">Select a journey to begin.</div>
          )}
          {selectedJourneyId !== '' && activeTab === 'evo' && (
            <EVOField events={events} />
          )}
          {selectedJourneyId !== '' && activeTab === 'flume' && (
            <EVOField events={events} />
          )}
          {selectedJourneyId !== '' && activeTab === 'quadrature' && (
            <QuadraturePanel journeyId={selectedJourneyId} />
          )}
          {selectedJourneyId !== '' && activeTab === 'narrate' && (
            <NarratePanel journeyId={selectedJourneyId} />
          )}
          {selectedJourneyId !== '' && activeTab === 'ask' && (
            <AskOmni journeyId={selectedJourneyId} />
          )}
        </div>
      </main>
    </div>
  );
}
