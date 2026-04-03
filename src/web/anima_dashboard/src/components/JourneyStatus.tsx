"use client";

import React, { useState, useEffect } from 'react';
import { Activity, Clock, Thermometer, Zap, Pause, Play } from 'lucide-react';

interface JourneyStatusData {
  journey_id: string;
  state: 'running' | 'paused' | 'completed' | 'error';
  elapsed_hours: number;
  total_hours: number;
  domains_completed: number;
  total_domains: number;
  hypotheses_completed: number;
  total_hypotheses: number;
  current_domain: string;
  current_hypothesis: string;
  gpu_temp: number;
  cpu_temp: number;
  tdp_consumed_percent: number;
  thermal_events: number;
  total_paused_minutes: number;
  coherence: number;
}

/**
 * Real-time journey status display for 8-hour autoresearch.
 * Shows thermal status, TDP budget, and execution progress.
 */
export default function JourneyStatus({ 
  data,
  onPauseResume 
}: { 
  data?: JourneyStatusData;
  onPauseResume?: () => void;
}) {
  const [localData, setLocalData] = useState<JourneyStatusData | null>(null);
  const [isPaused, setIsPaused] = useState(false);

  useEffect(() => {
    if (data) {
      setLocalData(data);
      setIsPaused(data.state === 'paused');
    }
  }, [data]);

  // Fallback data for demo
  const displayData = localData || {
    journey_id: "8hr_demo",
    state: 'running' as const,
    elapsed_hours: 3.5,
    total_hours: 8.0,
    domains_completed: 1,
    total_domains: 4,
    hypotheses_completed: 8,
    total_hypotheses: 20,
    current_domain: "gpu_kernel_optimization",
    current_hypothesis: "Optimize MXFP4 GEMM kernel via parameter tuning",
    gpu_temp: 78,
    cpu_temp: 72,
    tdp_consumed_percent: 45,
    thermal_events: 1,
    total_paused_minutes: 5.2,
    coherence: 0.67
  };

  const progressPercent = (displayData.elapsed_hours / displayData.total_hours) * 100;
  const tdpWarning = displayData.tdp_consumed_percent > 70;
  const tdpCritical = displayData.tdp_consumed_percent > 85;
  const tempWarning = displayData.gpu_temp > 85 || displayData.cpu_temp > 85;
  const tempCritical = displayData.gpu_temp > 90 || displayData.cpu_temp > 90;

  return (
    <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-6 shadow-2xl relative overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold font-mono text-emerald-400 flex items-center gap-2">
          <Activity className="w-5 h-5" />
          8-HOUR JOURNEY STATUS
        </h2>
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 rounded-full text-xs font-mono font-bold ${
            displayData.state === 'running' ? 'bg-emerald-500/20 text-emerald-400' :
            displayData.state === 'paused' ? 'bg-amber-500/20 text-amber-400' :
            displayData.state === 'completed' ? 'bg-blue-500/20 text-blue-400' :
            'bg-red-500/20 text-red-400'
          }`}>
            {displayData.state.toUpperCase()}
          </span>
          {onPauseResume && (
            <button
              onClick={() => {
                setIsPaused(!isPaused);
                onPauseResume();
              }}
              className="p-2 bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 transition-all"
            >
              {isPaused ? <Play className="w-4 h-4 text-emerald-400" /> : <Pause className="w-4 h-4 text-amber-400" />}
            </button>
          )}
        </div>
      </div>

      {/* Progress Bar */}
      <div className="mb-6">
        <div className="flex justify-between text-xs font-mono text-gray-400 mb-2">
          <span>Elapsed: {displayData.elapsed_hours.toFixed(1)}h / {displayData.total_hours}h</span>
          <span>{progressPercent.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-900 rounded-full h-2 overflow-hidden">
          <div
            className="h-2 rounded-full bg-gradient-to-r from-emerald-500 to-cyan-500 transition-all duration-500"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Domains */}
        <div className="p-4 bg-black/40 rounded-xl border border-white/5">
          <div className="text-xs text-gray-500 font-mono mb-1">DOMAINS</div>
          <div className="text-2xl font-bold font-mono text-white">
            {displayData.domains_completed}/{displayData.total_domains}
          </div>
          <div className="text-xs text-gray-600 font-mono mt-1">
            {((displayData.domains_completed / displayData.total_domains) * 100).toFixed(0)}%
          </div>
        </div>

        {/* Hypotheses */}
        <div className="p-4 bg-black/40 rounded-xl border border-white/5">
          <div className="text-xs text-gray-500 font-mono mb-1">HYPOTHESES</div>
          <div className="text-2xl font-bold font-mono text-cyan-400">
            {displayData.hypotheses_completed}/{displayData.total_hypotheses}
          </div>
          <div className="text-xs text-gray-600 font-mono mt-1">
            {((displayData.hypotheses_completed / displayData.total_hypotheses) * 100).toFixed(0)}%
          </div>
        </div>

        {/* Coherence */}
        <div className="p-4 bg-black/40 rounded-xl border border-white/5">
          <div className="text-xs text-gray-500 font-mono mb-1">HIHO COHERENCE</div>
          <div className={`text-2xl font-bold font-mono ${
            displayData.coherence >= 0.5 ? 'text-emerald-400' : 'text-amber-400'
          }`}>
            {(displayData.coherence ?? 0).toFixed(2)}
          </div>
          <div className="text-xs text-gray-600 font-mono mt-1">
            {displayData.coherence >= 0.5 ? 'ABOVE THRESHOLD' : 'BELOW THRESHOLD'}
          </div>
        </div>

        {/* Thermal Events */}
        <div className="p-4 bg-black/40 rounded-xl border border-white/5">
          <div className="text-xs text-gray-500 font-mono mb-1">THERMAL EVENTS</div>
          <div className={`text-2xl font-bold font-mono ${
            displayData.thermal_events === 0 ? 'text-emerald-400' : 
            displayData.thermal_events < 3 ? 'text-amber-400' : 'text-red-400'
          }`}>
            {displayData.thermal_events}
          </div>
          <div className="text-xs text-gray-600 font-mono mt-1">
            {displayData.total_paused_minutes.toFixed(1)} min paused
          </div>
        </div>
      </div>

      {/* Current Activity */}
      <div className="mb-6 p-4 bg-emerald-500/5 border border-emerald-500/20 rounded-xl">
        <div className="text-xs text-emerald-400 font-mono mb-2 flex items-center gap-2">
          <Clock className="w-3 h-3" />
          CURRENT ACTIVITY
        </div>
        <div className="text-sm text-white font-mono mb-1">
          Domain: <span className="text-emerald-300">{displayData.current_domain.replace(/_/g, ' ')}</span>
        </div>
        <div className="text-xs text-gray-400 font-mono leading-relaxed">
          {displayData.current_hypothesis}
        </div>
      </div>

      {/* Thermal & Power Status */}
      <div className="grid grid-cols-2 gap-4">
        {/* Temperature */}
        <div className={`p-4 rounded-xl border ${
          tempCritical ? 'bg-red-500/10 border-red-500/30' :
          tempWarning ? 'bg-amber-500/10 border-amber-500/30' :
          'bg-black/40 border-white/5'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <Thermometer className={`w-4 h-4 ${
              tempCritical ? 'text-red-400' :
              tempWarning ? 'text-amber-400' :
              'text-emerald-400'
            }`} />
            <span className="text-xs font-mono text-gray-400">TEMPERATURES</span>
          </div>
          <div className="flex justify-between items-center mb-2">
            <span className="text-xs text-gray-500">GPU</span>
            <span className={`font-mono font-bold ${
              displayData.gpu_temp > 90 ? 'text-red-400' :
              displayData.gpu_temp > 85 ? 'text-amber-400' :
              'text-emerald-400'
            }`}>
              {displayData.gpu_temp}°C
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-xs text-gray-500">CPU</span>
            <span className={`font-mono font-bold ${
              displayData.cpu_temp > 90 ? 'text-red-400' :
              displayData.cpu_temp > 85 ? 'text-amber-400' :
              'text-emerald-400'
            }`}>
              {displayData.cpu_temp}°C
            </span>
          </div>
        </div>

        {/* TDP Budget */}
        <div className={`p-4 rounded-xl border ${
          tdpCritical ? 'bg-red-500/10 border-red-500/30' :
          tdpWarning ? 'bg-amber-500/10 border-amber-500/30' :
          'bg-black/40 border-white/5'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <Zap className={`w-4 h-4 ${
              tdpCritical ? 'text-red-400' :
              tdpWarning ? 'text-amber-400' :
              'text-emerald-400'
            }`} />
            <span className="text-xs font-mono text-gray-400">TDP BUDGET</span>
          </div>
          <div className="mb-2">
            <div className="flex justify-between text-xs font-mono mb-1">
              <span className="text-gray-500">Consumed</span>
              <span className={tdpCritical ? 'text-red-400' : tdpWarning ? 'text-amber-400' : 'text-emerald-400'}>
                {displayData.tdp_consumed_percent.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-gray-900 rounded-full h-1.5 overflow-hidden">
              <div
                className={`h-1.5 rounded-full transition-all duration-500 ${
                  tdpCritical ? 'bg-red-500' :
                  tdpWarning ? 'bg-amber-500' :
                  'bg-emerald-500'
                }`}
                style={{ width: `${Math.min(displayData.tdp_consumed_percent, 100)}%` }}
              />
            </div>
          </div>
          <div className="text-xs text-gray-600 font-mono">
            {(100 - displayData.tdp_consumed_percent).toFixed(1)}% remaining
          </div>
        </div>
      </div>

      {/* Journey ID */}
      <div className="mt-6 pt-4 border-t border-white/5 text-center">
        <span className="text-[10px] text-gray-600 font-mono">
          Journey ID: {displayData.journey_id}
        </span>
      </div>
    </div>
  );
}
