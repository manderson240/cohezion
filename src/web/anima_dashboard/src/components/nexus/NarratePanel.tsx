import { useEffect, useState } from 'react';

interface TrajectoryPoint {
  coherence: number;
}

interface NarrateResult {
  text: string;
  audio_b64: string;
  image_b64?: string;
  trajectory?: TrajectoryPoint[];
}

function NarratePanel({ journeyId }: { journeyId: string }) {
  const [data, setData] = useState<NarrateResult | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/journey-nexus/narrate/${journeyId}?with_image=true`);
        if (!response.ok) {
          throw new Error(`Failed to fetch: ${response.status}`);
        }
        const result: NarrateResult = await response.json();
        setData(result);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'An unknown error occurred');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [journeyId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-600">Loading narrative...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 text-red-700 rounded-md border border-red-200">
        Error: {error}
      </div>
    );
  }

  if (!data) {
    return null;
  }

  // Generate sparkline path for coherence timeline
  const renderCoherenceTimeline = () => {
    const trajectory = data.trajectory ?? [];
    if (trajectory.length === 0) {
      // Default line showing 0.5
      return (
        <svg className="w-full h-12" viewBox="0 0 100 20" preserveAspectRatio="none">
          <line x1="0" y1="10" x2="100" y2="10" stroke="#94a3b8" strokeWidth="2" />
        </svg>
      );
    }

    const points = trajectory.map((p, i) => {
      const x = (i / (trajectory.length - 1)) * 100;
      // Normalize coherence to 0-20 range (assuming 0-1 range, map to 0-20)
      const y = 20 - (p.coherence * 20);
      return `${x},${y}`;
    });

    return (
      <svg className="w-full h-12" viewBox="0 0 100 20" preserveAspectRatio="none">
        <polyline
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
          points={points.join(' ')}
        />
      </svg>
    );
  };

  return (
    <div className="space-y-6 p-4 bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Text Content */}
      <blockquote className="relative p-4 border-l-4 border-blue-500 bg-blue-50 italic text-gray-700">
        {data.text}
      </blockquote>

      {/* Audio Player */}
      <div className="w-full">
        <audio controls className="w-full">
          <source src={`data:audio/mpeg;base64,${data.audio_b64}`} type="audio/mpeg" />
          Your browser does not support the audio element.
        </audio>
      </div>

      {/* Image Carousel (Single Image) */}
      {data.image_b64 && (
        <div className="w-full overflow-hidden rounded-lg border border-gray-200">
          {/* eslint-disable-next-line @next/next/no-img-element -- data: URI, no LCP impact */}
          <img
            src={`data:image/png;base64,${data.image_b64}`}
            alt="Narrative visualization"
            className="w-full h-auto object-cover"
          />
        </div>
      )}

      {/* Coherence Timeline */}
      <div className="mt-4">
        <h4 className="text-sm font-medium text-gray-500 mb-2">Coherence Trajectory</h4>
        {renderCoherenceTimeline()}
      </div>
    </div>
  );
}

export default NarratePanel;
