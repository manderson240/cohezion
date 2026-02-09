import { useEffect, useRef } from 'react';

/**
 * HIHO Sonification Engine - HomeostasisHarmonics
 * 
 * Maps 12D manifold stability to audio frequencies.
 * Protocol: Map field transitions to audio frequencies based on distance from 0.5.
 */
export const useHomeostasisHarmonics = (coherence: number, active: boolean) => {
    const audioCtxRef = useRef<AudioContext | null>(null);
    const oscillatorRef = useRef<OscillatorNode | null>(null);
    const gainNodeRef = useRef<GainNode | null>(null);

    useEffect(() => {
        if (!active) {
            if (audioCtxRef.current) {
                audioCtxRef.current.close();
                audioCtxRef.current = null;
            }
            return;
        }

        if (!audioCtxRef.current) {
            audioCtxRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();

            gainNodeRef.current = audioCtxRef.current.createGain();
            gainNodeRef.current.gain.value = 0.05; // Base volume
            gainNodeRef.current.connect(audioCtxRef.current.destination);

            oscillatorRef.current = audioCtxRef.current.createOscillator();
            oscillatorRef.current.type = 'sine';
            oscillatorRef.current.connect(gainNodeRef.current);
            oscillatorRef.current.start();
        }

        if (oscillatorRef.current && gainNodeRef.current && audioCtxRef.current) {
            // Mapping Logic:
            // 0.5 = Perfect stability = Neutral tone (440Hz)
            // Deviance from 0.5 = Higher/Lower frequencies

            const distFromHIHO = Math.abs(coherence - 0.5);
            const frequency = 440 + (distFromHIHO * 200); // 440Hz to 540Hz mapping

            const now = audioCtxRef.current.currentTime;
            oscillatorRef.current.frequency.exponentialRampToValueAtTime(frequency, now + 0.1);

            // Volume modulation based on activity
            const volume = 0.05 + (distFromHIHO * 0.1);
            gainNodeRef.current.gain.linearRampToValueAtTime(volume, now + 0.1);
        }
    }, [coherence, active]);
};
