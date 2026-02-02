import init, { DualStateManifold } from '../pkg/cohezion_core_rs';

const manifolds = new Map<string, DualStateManifold>();
let initialized = false;

self.onmessage = async (e) => {
    const { type, data } = e.data;

    switch (type) {
        case 'INIT':
            if (!initialized) {
                await init();
                initialized = true;
                self.postMessage({ type: 'READY' });
            }
            break;

        case 'HYDRATE':
            if (!initialized) return;
            // data: { id, latent: float32array }
            const { id, latent } = data;
            let manifold = manifolds.get(id);
            if (!manifold) {
                manifold = new DualStateManifold();
                manifolds.set(id, manifold);
            }
            manifold.hydrate(latent);
            break;

        case 'TICK':
            if (!initialized) return;
            // data: { dt }
            const { dt } = data;
            const results: Record<string, { axiomatic: Float32Array; visibility: number }> = {};

            manifolds.forEach((manifold, agentId) => {
                manifold.evolve_axiomatic(dt);
                results[agentId] = {
                    axiomatic: manifold.get_axiomatic(),
                    visibility: manifold.get_visibility()
                };
            });

            self.postMessage({ type: 'PULSE', results });
            break;

        case 'TERMINATE':
            self.close();
            break;
    }
};
