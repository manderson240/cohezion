-- Cohezion Brand Identity Projection
-- Namespace: cohezion, Database: identity

REMOVE TABLE brand_identity;
DEFINE TABLE brand_identity SCHEMAFULL;
DEFINE FIELD name ON brand_identity TYPE string;
DEFINE FIELD tagline ON brand_identity TYPE string;
DEFINE FIELD philosophy ON brand_identity TYPE string;
DEFINE FIELD colors ON brand_identity TYPE object;
DEFINE FIELD motifs ON brand_identity TYPE array;
DEFINE FIELD last_updated ON brand_identity TYPE datetime;

CREATE brand_identity:nexus CONTENT {
    name: 'Cohezion',
    tagline: 'The Nexus of Coherence',
    philosophy: 'Organic Modularity',
    colors: {
        nexus_green: '#00FF00',
        matte_black: '#0A0A0A',
        silicon_silver: '#C0C0C0',
        earth_blue: '#0077BE'
    },
    motifs: [
        'Performance Delta',
        'Lattice Grid',
        'Open Singularity'
    ],
    logo_path: '/home/mike-anderson/.gemini/antigravity/brain/2affbcca-b8be-4a9f-a143-509531a03543/cohezion_nexus_logo_refined_1769101905406.png',
    last_updated: time::now()
};
