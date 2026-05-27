"use client";

import React, { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

export default function StealthskaterView() {
  // --- State for LENR ---
  const [lenrCoh, setLenrCoh] = useState<number>(0.5);
  const [lenrCoupling, setLenrCoupling] = useState<number>(1.0);
  const [lenrThreshold, setLenrThreshold] = useState<number>(0.5);
  const [lenrRate, setLenrRate] = useState<number>(1.0);
  const [lenrEvents, setLenrEvents] = useState<number>(0);
  const [lenrMeanRate, setLenrMeanRate] = useState<number>(0.0);
  const [lenrLog, setLenrLog] = useState<string[]>([]);

  // --- State for Ionic Cluster ---
  const [ionicDensity, setIonicDensity] = useState<number>(0.5);
  const [ionicSize, setIonicSize] = useState<number>(100);
  const [ionicTolerance, setIonicTolerance] = useState<number>(0.05);
  const [ionicStatus, setIonicStatus] = useState({
    hiho_equilibrium: true,
    ionisation_rate: 1.0,
    active_ions: 50,
    steps_taken: 0,
  });

  // --- State for Dielectric ---
  const [dielectricVoltage, setDielectricVoltage] = useState<number>(10000);
  const [dielectricSeparation, setDielectricSeparation] = useState<number>(0.01);
  const [dielectricPerm, setDielectricPerm] = useState<[number, number, number]>([1.0, 1.0, 1.0]);
  const [dielectricResult, setDielectricResult] = useState({
    mean_permittivity: 1.0,
    biefield_brown_force: [0.0, 0.0, 0.0],
    gauge_connection_potential: [
      [0.0, 0.0, 0.0],
      [0.0, 0.0, 0.0],
      [0.0, 0.0, 0.0],
    ],
  });

  // --- State for Sarfatti & QGP ---
  const [sarfattiCoh, setSarfattiCoh] = useState<number>(0.5);
  const [sarfattiDestiny, setSarfattiDestiny] = useState<number>(0.5);
  const [sarfattiResult, setSarfattiResult] = useState({
    back_action_amplitude: 0.5,
    metric_coupling: 0.5,
    hiho_attractor_engaged: true,
  });

  const [qgpCoh, setQgpCoh] = useState<number>(0.5);
  const [qgpTemp, setQgpTemp] = useState<number>(155.0);
  const [qgpResult, setQgpResult] = useState({
    deconfinement_rate: 1.0,
    qcd_hiho: true,
    is_deconfined: false,
    chromatic_coherence: 1.0,
  });

  const [mode, setMode] = useState<"api" | "local">("api");

  // --- Fetch & Simulation Handlers ---
  const fetchLenr = useCallback(async () => {
    try {
      const resp = await fetch(
        `${API_BASE}/api/physics/lenr/simulate?coherence=${lenrCoh}&reaction_threshold=${lenrThreshold}&lattice_coupling=${lenrCoupling}`
      );
      if (resp.ok) {
        const data = await resp.json();
        setLenrRate(data.reaction_rate);
        setMode("api");
        return;
      }
    } catch {
      // Fallback to local computation
    }
    // Local calculation
    const t = lenrThreshold;
    if (t > 0 && t < 1) {
      const peak = 4.0 * t * (1.0 - t);
      const c = Math.max(0, Math.min(1, lenrCoh));
      const rate = lenrCoupling * (c * (1.0 - c) / (t * (1.0 - t))) * peak;
      setLenrRate(rate);
      setMode("local");
    }
  }, [lenrCoh, lenrThreshold, lenrCoupling]);

  const triggerLenrEvent = async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/physics/lenr/event`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ coherence: lenrCoh, agent_id: "dashboard-lenr" }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setLenrEvents(data.event_count);
        setLenrMeanRate(data.mean_rate);
        setLenrLog((prev) => [
          `[LENR Event] Coherence: ${lenrCoh.toFixed(3)}, Rate: ${data.reaction_rate.toFixed(4)} (Count: ${data.event_count})`,
          ...prev.slice(0, 9),
        ]);
        return;
      }
    } catch {
      // Local event fallback
    }
    // Local state fallback
    const rate = lenrRate;
    setLenrEvents((prev) => prev + 1);
    setLenrMeanRate((prev) => {
      const count = lenrEvents + 1;
      return (prev * lenrEvents + rate) / count;
    });
    setLenrLog((prev) => [
      `[Local Event] Coherence: ${lenrCoh.toFixed(3)}, Rate: ${rate.toFixed(4)}`,
      ...prev.slice(0, 9),
    ]);
  };

  const fetchIonic = useCallback(async () => {
    try {
      const resp = await fetch(
        `${API_BASE}/api/physics/ionic-cluster/status?agent_id=dashboard-ionic&plasma_density=${ionicDensity}&cluster_size=${ionicSize}&hiho_tolerance=${ionicTolerance}`
      );
      if (resp.ok) {
        const data = await resp.json();
        setIonicStatus({
          hiho_equilibrium: data.hiho_equilibrium,
          ionisation_rate: data.ionisation_rate,
          active_ions: data.active_ions,
          steps_taken: data.steps_taken,
        });
        return;
      }
    } catch {
      // Fallback
    }
    // Local fallback calculations
    const eq = Math.abs(ionicDensity - 0.5) <= ionicTolerance;
    const rate = 4.0 * ionicDensity * (1.0 - ionicDensity);
    setIonicStatus((prev) => ({
      hiho_equilibrium: eq,
      ionisation_rate: rate,
      active_ions: Math.round(ionicSize * ionicDensity),
      steps_taken: prev.steps_taken,
    }));
  }, [ionicDensity, ionicSize, ionicTolerance]);

  const stepIonic = async (delta: number) => {
    try {
      const resp = await fetch(`${API_BASE}/api/physics/ionic-cluster/step`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ delta, agent_id: "dashboard-ionic" }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setIonicDensity(data.plasma_density);
        setIonicStatus((prev) => ({
          ...prev,
          hiho_equilibrium: data.hiho_equilibrium,
          active_ions: data.active_ions,
          steps_taken: data.steps_taken,
        }));
        return;
      }
    } catch {
      // Fallback
    }
    // Local step
    const nextDensity = Math.max(0, Math.min(1, ionicDensity + delta));
    setIonicDensity(nextDensity);
    setIonicStatus((prev) => ({
      ...prev,
      steps_taken: prev.steps_taken + 1,
    }));
  };

  const fetchDielectric = useCallback(async () => {
    const permString = dielectricPerm.join(",");
    try {
      const resp = await fetch(
        `${API_BASE}/api/physics/dielectric/polarization?voltage=${dielectricVoltage}&electrode_separation=${dielectricSeparation}&permittivity_diagonal=${permString}`
      );
      if (resp.ok) {
        const data = await resp.json();
        setDielectricResult({
          mean_permittivity: data.mean_permittivity,
          biefield_brown_force: data.biefield_brown_force,
          gauge_connection_potential: data.gauge_connection_potential,
        });
        return;
      }
    } catch {
      // Fallback
    }
    // Local EHD math
    const meanPerm = (dielectricPerm[0] + dielectricPerm[1] + dielectricPerm[2]) / 3;
    const eps0 = 8.854e-12;
    const eField = dielectricVoltage / Math.max(dielectricSeparation, 1e-9);
    const forceMagnitude = eps0 * meanPerm * eField ** 2 * 1e-4; // 1cm^2 area proxy
    // Thrust direction: align to z axis deviation
    setDielectricResult({
      mean_permittivity: meanPerm,
      biefield_brown_force: [0, 0, forceMagnitude],
      gauge_connection_potential: [
        [0, 0, 0],
        [0, 0, 0],
        [dielectricPerm[0] - 1, dielectricPerm[1] - 1, dielectricPerm[2] - 1],
      ],
    });
  }, [dielectricVoltage, dielectricSeparation, dielectricPerm]);

  const fetchSarfatti = useCallback(async () => {
    try {
      const resp = await fetch(
        `${API_BASE}/api/physics/sarfatti/backaction?coherence=${sarfattiCoh}&destiny_weight=${sarfattiDestiny}`
      );
      if (resp.ok) {
        const data = await resp.json();
        setSarfattiResult({
          back_action_amplitude: data.back_action_amplitude,
          metric_coupling: data.metric_coupling,
          hiho_attractor_engaged: data.hiho_attractor_engaged,
        });
        return;
      }
    } catch {
      // Fallback
    }
    const amp = sarfattiDestiny * 4.0 * sarfattiCoh * (1.0 - sarfattiCoh);
    setSarfattiResult({
      back_action_amplitude: amp,
      metric_coupling: amp,
      hiho_attractor_engaged: Math.abs(sarfattiCoh - 0.5) <= 0.05,
    });
  }, [sarfattiCoh, sarfattiDestiny]);

  const fetchQgp = useCallback(async () => {
    try {
      const resp = await fetch(
        `${API_BASE}/api/physics/qgp/status?quark_coherence=${qgpCoh}&temperature_mev=${qgpTemp}`
      );
      if (resp.ok) {
        const data = await resp.json();
        setQgpResult({
          deconfinement_rate: data.deconfinement_rate,
          qcd_hiho: data.qcd_hiho,
          is_deconfined: data.is_deconfined,
          chromatic_coherence: data.chromatic_coherence,
        });
        return;
      }
    } catch {
      // Fallback
    }
    const rate = 4.0 * qgpCoh * (1.0 - qgpCoh);
    setQgpResult({
      deconfinement_rate: rate,
      qcd_hiho: Math.abs(qgpCoh - 0.5) <= 0.05,
      is_deconfined: qgpTemp > 155.0,
      chromatic_coherence: rate,
    });
  }, [qgpCoh, qgpTemp]);

  // --- Run Fetch Updates ---
  useEffect(() => {
    fetchLenr();
  }, [fetchLenr]);

  useEffect(() => {
    fetchIonic();
  }, [fetchIonic]);

  useEffect(() => {
    fetchDielectric();
  }, [fetchDielectric]);

  useEffect(() => {
    fetchSarfatti();
    fetchQgp();
  }, [fetchSarfatti, fetchQgp]);

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 font-mono text-xs">
      {/* Column 1: Nuclear & Plasma */}
      <div className="space-y-6">
        {/* LENR Widget */}
        <div className="bg-black/90 border border-gray-800 rounded-xl p-5 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 px-3 py-1 bg-green-900/40 text-green-400 border-l border-b border-gray-800 rounded-bl text-[9px]">
            LENR Telemetry {mode === "local" ? "(Local)" : "(Live)"}
          </div>
          <h3 className="text-sm font-bold text-green-400 mb-4 flex items-center gap-2">
            ⚛️ Lattice-Confined Nuclear Reactions
          </h3>
          <p className="text-gray-500 mb-4 leading-relaxed">
            Nuclear transmutation rate peaks at exactly 0.5 coherence (HIHO), representing
            the optimal balance of phonon-mediated lattice coupling.
          </p>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-400">Coherence ($c$):</span>
                <span className="text-cyan-400 font-bold">{lenrCoh.toFixed(3)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={lenrCoh}
                onChange={(e) => setLenrCoh(parseFloat(e.target.value))}
                className="w-full accent-green-500 bg-gray-800 h-1 rounded-lg"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">Coupling ($k$):</span>
                  <span className="text-green-400 font-bold">{lenrCoupling.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min={0.1}
                  max={3.0}
                  step={0.1}
                  value={lenrCoupling}
                  onChange={(e) => setLenrCoupling(parseFloat(e.target.value))}
                  className="w-full accent-green-500 bg-gray-800 h-1 rounded-lg"
                />
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">Peak Threshold:</span>
                  <span className="text-yellow-400 font-bold">{lenrThreshold.toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={0.2}
                  max={0.8}
                  step={0.05}
                  value={lenrThreshold}
                  onChange={(e) => setLenrThreshold(parseFloat(e.target.value))}
                  className="w-full accent-green-500 bg-gray-800 h-1 rounded-lg"
                />
              </div>
            </div>

            {/* Reaction Rate visualizer */}
            <div className="bg-gray-950 border border-gray-900 rounded-lg p-3 flex justify-between items-center">
              <div>
                <div className="text-[10px] text-gray-500 mb-0.5">Calculated Transmutation Rate</div>
                <div className="text-xl font-bold text-green-400">
                  {lenrRate.toFixed(6)} <span className="text-[10px] text-gray-600">reactions/s</span>
                </div>
              </div>
              <button
                onClick={triggerLenrEvent}
                className="px-4 py-2 bg-green-950/40 text-green-400 border border-green-800 rounded hover:bg-green-900/30 transition-colors"
              >
                Log Reaction Event
              </button>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 text-[10px] bg-gray-950/40 p-2 rounded border border-gray-900">
              <div className="flex justify-between">
                <span className="text-gray-500">Event Logs:</span>
                <span className="text-gray-300 font-bold">{lenrEvents}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Mean Rate:</span>
                <span className="text-gray-300 font-bold">{lenrMeanRate.toFixed(4)}</span>
              </div>
            </div>

            {/* Event Console */}
            {lenrLog.length > 0 && (
              <div className="bg-black border border-gray-900 rounded p-2 h-20 overflow-y-auto text-[9px] text-gray-500 space-y-1 scrollbar-thin">
                {lenrLog.map((log, idx) => (
                  <div key={idx} className="font-mono">
                    ⚡ {log}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Ionic Cluster Widget */}
        <div className="bg-black/90 border border-gray-800 rounded-xl p-5 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 px-3 py-1 bg-cyan-900/40 text-cyan-400 border-l border-b border-gray-800 rounded-bl text-[9px]">
            Plasma Telemetry
          </div>
          <h3 className="text-sm font-bold text-cyan-400 mb-4 flex items-center gap-2">
            🌌 Self-Organised Ionic Cluster
          </h3>
          <p className="text-gray-500 mb-4 leading-relaxed">
            Plasma stability relies on HIHO equilibrium ($50\%$ ionization, half нейтральный gas). Steps taken modify density parameters.
          </p>

          <div className="space-y-4">
            <div>
              <div className="flex justify-between mb-1">
                <span className="text-gray-400">Plasma Ionization Density ($\rho$):</span>
                <span className="text-cyan-400 font-bold">{ionicDensity.toFixed(3)}</span>
              </div>
              <input
                type="range"
                min={0}
                max={1}
                step={0.01}
                value={ionicDensity}
                onChange={(e) => setIonicDensity(parseFloat(e.target.value))}
                className="w-full accent-cyan-500 bg-gray-800 h-1 rounded-lg"
              />
            </div>

            <div className="grid grid-cols-3 gap-2 bg-gray-950/40 p-3 rounded-lg border border-gray-900">
              <div className="text-center">
                <div className="text-[9px] text-gray-600">Active Ions</div>
                <div className="text-sm font-bold text-cyan-400">{ionicStatus.active_ions} / {ionicSize}</div>
              </div>
              <div className="text-center border-x border-gray-900">
                <div className="text-[9px] text-gray-600">Ionisation Rate</div>
                <div className="text-sm font-bold text-green-400">{ionicStatus.ionisation_rate.toFixed(4)}</div>
              </div>
              <div className="text-center">
                <div className="text-[9px] text-gray-600">Equilibrium Status</div>
                <div
                  className={`text-xs font-bold px-1.5 py-0.5 rounded inline-block mt-0.5 ${
                    ionicStatus.hiho_equilibrium
                      ? "bg-green-950/40 text-green-400 border border-green-800"
                      : "bg-red-950/40 text-red-400 border border-red-900"
                  }`}
                >
                  {ionicStatus.hiho_equilibrium ? "EQUILIBRIUM" : "UNSTABLE"}
                </div>
              </div>
            </div>

            {/* Stepping controls */}
            <div className="flex justify-between gap-3">
              <button
                onClick={() => stepIonic(-0.02)}
                className="flex-1 py-2 bg-gray-900 hover:bg-gray-800 border border-gray-800 text-gray-400 hover:text-gray-200 rounded transition-colors"
              >
                Recombine (-0.02)
              </button>
              <button
                onClick={() => stepIonic(0.02)}
                className="flex-1 py-2 bg-cyan-950/40 hover:bg-cyan-900/30 border border-cyan-800 text-cyan-400 rounded transition-colors"
              >
                Ionise (+0.02)
              </button>
            </div>

            <div className="flex justify-between text-[10px] text-gray-600">
              <span>Cluster Size: {ionicSize} species</span>
              <span>Simulation Steps Taken: {ionicStatus.steps_taken}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Column 2: Dielectric, Retrocausality, QGP */}
      <div className="space-y-6">
        {/* Dielectric Widget */}
        <div className="bg-black/90 border border-gray-800 rounded-xl p-5 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 px-3 py-1 bg-purple-900/40 text-purple-400 border-l border-b border-gray-800 rounded-bl text-[9px]">
            Dielectric Field
          </div>
          <h3 className="text-sm font-bold text-purple-400 mb-4 flex items-center gap-2">
            ⚡ Anisotropic EHD Polarization
          </h3>
          <p className="text-gray-500 mb-4 leading-relaxed">
            The Biefield-Brown EHD thrust vectors are driven by asymmetric dielectric loading
            which maps to U(1) gauge potentials.
          </p>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">Voltage ($V$):</span>
                  <span className="text-purple-400 font-bold">{dielectricVoltage} V</span>
                </div>
                <input
                  type="range"
                  min={5000}
                  max={25000}
                  step={1000}
                  value={dielectricVoltage}
                  onChange={(e) => setDielectricVoltage(parseInt(e.target.value))}
                  className="w-full accent-purple-500 bg-gray-800 h-1 rounded-lg"
                />
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-gray-400">Separation ($d$):</span>
                  <span className="text-purple-400 font-bold">{(dielectricSeparation * 100).toFixed(1)} cm</span>
                </div>
                <input
                  type="range"
                  min={0.005}
                  max={0.03}
                  step={0.001}
                  value={dielectricSeparation}
                  onChange={(e) => setDielectricSeparation(parseFloat(e.target.value))}
                  className="w-full accent-purple-500 bg-gray-800 h-1 rounded-lg"
                />
              </div>
            </div>

            {/* Permittivity Tensor adjustments */}
            <div>
              <span className="text-gray-400 block mb-2">Dielectric Permittivity Diagonal ($\varepsilon_r$):</span>
              <div className="grid grid-cols-3 gap-2">
                {[0, 1, 2].map((idx) => (
                  <div key={idx} className="bg-gray-950 p-2 rounded border border-gray-900">
                    <div className="flex justify-between text-[9px] mb-1">
                      <span className="text-gray-600">Axis {idx === 0 ? "X" : idx === 1 ? "Y" : "Z"}:</span>
                      <span className="text-cyan-400 font-bold">{dielectricPerm[idx].toFixed(1)}</span>
                    </div>
                    <input
                      type="range"
                      min={1.0}
                      max={5.0}
                      step={0.2}
                      value={dielectricPerm[idx]}
                      onChange={(e) => {
                        const newPerm = [...dielectricPerm] as [number, number, number];
                        newPerm[idx] = parseFloat(e.target.value);
                        setDielectricPerm(newPerm);
                      }}
                      className="w-full accent-purple-500 bg-gray-800 h-1 rounded-lg"
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* EHD Thrust Visualizer */}
            <div className="bg-gray-950 border border-gray-900 rounded-lg p-3 grid grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] text-gray-500 mb-0.5">Mean Permittivity</div>
                <div className="text-md font-bold text-gray-300">
                  {dielectricResult.mean_permittivity.toFixed(3)}
                </div>
                <div className="text-[10px] text-gray-500 mb-0.5 mt-2">Biefield-Brown Force Vector</div>
                <div className="text-[11px] font-bold text-purple-400">
                  F_z = {dielectricResult.biefield_brown_force[2].toFixed(6)} N
                </div>
              </div>

              {/* Gauge connection potential visual */}
              <div>
                <div className="text-[10px] text-gray-500 mb-1">U(1) Gauge Connection Row</div>
                <div className="bg-black/90 p-2 rounded font-mono text-[10px] border border-gray-900 space-y-1 text-gray-400">
                  <div>A_x: {dielectricResult.gauge_connection_potential[2]?.[0].toFixed(2)}</div>
                  <div>A_y: {dielectricResult.gauge_connection_potential[2]?.[1].toFixed(2)}</div>
                  <div>A_z: {dielectricResult.gauge_connection_potential[2]?.[2].toFixed(2)}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Sarfatti & QGP Panel */}
        <div className="bg-black/90 border border-gray-800 rounded-xl p-5 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 px-3 py-1 bg-yellow-900/40 text-yellow-400 border-l border-b border-gray-800 rounded-bl text-[9px]">
            Post-Quantum & QCD
          </div>
          <h3 className="text-sm font-bold text-yellow-400 mb-4 flex items-center gap-2">
            🌀 Sarfatti Back-Action & QGP Crossover
          </h3>

          <div className="space-y-4">
            {/* Sarfatti Slider */}
            <div>
              <h4 className="text-[11px] text-yellow-500 font-bold mb-2">Sarfatti Retrocausality</h4>
              <div className="grid grid-cols-2 gap-4 mb-2">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] text-gray-400">Coherence:</span>
                    <span className="text-cyan-400 font-bold">{sarfattiCoh.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={sarfattiCoh}
                    onChange={(e) => setSarfattiCoh(parseFloat(e.target.value))}
                    className="w-full accent-yellow-500 bg-gray-800 h-1 rounded-lg"
                  />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] text-gray-400">Destiny Weight:</span>
                    <span className="text-yellow-400 font-bold">{sarfattiDestiny.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={sarfattiDestiny}
                    onChange={(e) => setSarfattiDestiny(parseFloat(e.target.value))}
                    className="w-full accent-yellow-500 bg-gray-800 h-1 rounded-lg"
                  />
                </div>
              </div>
              <div className="bg-gray-950 p-2 rounded border border-gray-900 text-[10px] space-y-1 text-gray-400">
                <div className="flex justify-between">
                  <span>Back-Action Pull:</span>
                  <span className="text-yellow-400 font-bold">{sarfattiResult.back_action_amplitude.toFixed(4)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Metric Curvature Coupling:</span>
                  <span className="text-purple-400 font-bold">{sarfattiResult.metric_coupling.toFixed(4)}</span>
                </div>
                <div className="flex justify-between">
                  <span>HIHO Attractor Status:</span>
                  <span className={sarfattiResult.hiho_attractor_engaged ? "text-green-400 font-bold" : "text-gray-600"}>
                    {sarfattiResult.hiho_attractor_engaged ? "ENGAGED" : "DORMANT"}
                  </span>
                </div>
              </div>
            </div>

            {/* QGP Widget */}
            <div className="border-t border-gray-900 pt-3">
              <h4 className="text-[11px] text-yellow-500 font-bold mb-2">QCD Quark-Gluon Plasma</h4>
              <div className="grid grid-cols-2 gap-4 mb-2">
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] text-gray-400">Quark Coherence:</span>
                    <span className="text-cyan-400 font-bold">{qgpCoh.toFixed(2)}</span>
                  </div>
                  <input
                    type="range"
                    min={0}
                    max={1}
                    step={0.05}
                    value={qgpCoh}
                    onChange={(e) => setQgpCoh(parseFloat(e.target.value))}
                    className="w-full accent-yellow-500 bg-gray-800 h-1 rounded-lg"
                  />
                </div>
                <div>
                  <div className="flex justify-between mb-1">
                    <span className="text-[10px] text-gray-400">Temperature ($T$):</span>
                    <span className="text-red-400 font-bold">{qgpTemp.toFixed(1)} MeV</span>
                  </div>
                  <input
                    type="range"
                    min={100}
                    max={200}
                    step={2}
                    value={qgpTemp}
                    onChange={(e) => setQgpTemp(parseFloat(e.target.value))}
                    className="w-full accent-yellow-500 bg-gray-800 h-1 rounded-lg"
                  />
                </div>
              </div>
              <div className="bg-gray-950 p-2 rounded border border-gray-900 text-[10px] space-y-1 text-gray-400">
                <div className="flex justify-between">
                  <span>Deconfinement Crossover Rate:</span>
                  <span className="text-green-400 font-bold">{qgpResult.deconfinement_rate.toFixed(4)}</span>
                </div>
                <div className="flex justify-between">
                  <span>QCD Phase:</span>
                  <span className={qgpResult.is_deconfined ? "text-red-400 font-bold animate-pulse" : "text-blue-400 font-bold"}>
                    {qgpResult.is_deconfined ? "DECONFINED (QGP)" : "CONFINED (HADRONS)"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>QCD HIHO Equilibrium:</span>
                  <span className={qgpResult.qcd_hiho ? "text-green-400 font-bold" : "text-gray-600"}>
                    {qgpResult.qcd_hiho ? "CRITICAL BALANCE" : "OFF-CRITICAL"}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Full Width Explanatory Card */}
      <div className="xl:col-span-2 bg-[#050510]/60 border border-gray-800 rounded-xl p-5 shadow-2xl font-mono text-[11px] text-gray-400 leading-relaxed space-y-4">
        <h4 className="text-xs text-green-400 font-bold flex items-center gap-1.5">
          📖 Matsumoto Electro-Nuclear Collapse (ENC) & The 17th Worldview Tradition
        </h4>
        <p>
          In the Cohezion compound engineering framework, we map Matsumoto&apos;s ENC tradition (itonic equilibrium)
          as our 17th tradition worldview. Under this view, lattice coherence at exactly the $0.5$ HIHO threshold
          represents a balance between the past (causal propagation) and the future (destiny-state back-action).
          This balance drives maximum entropy at the informational boundary, permitting stable reality precipitation
          without thermal collapse.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[10px] pt-1">
          <div className="bg-black/50 p-3 rounded border border-gray-900">
            <span className="text-cyan-400 font-bold block mb-1">Vacuum Ground (Step 0)</span>
            Matsumoto zero-point fluctuation (ZPF) ground state maps to Brahmagupta&apos;s void.
          </div>
          <div className="bg-black/50 p-3 rounded border border-gray-900">
            <span className="text-yellow-400 font-bold block mb-1">Crossover Equilibrium</span>
            Active plasma density step-coupling maintains self-organized stability.
          </div>
          <div className="bg-black/50 p-3 rounded border border-gray-900">
            <span className="text-purple-400 font-bold block mb-1">Spacetime Metric Coupling</span>
            Biefield-Brown asymmetric polarization generates net thrust via U(1) gauge conexión potential.
          </div>
        </div>
      </div>
    </div>
  );
}
