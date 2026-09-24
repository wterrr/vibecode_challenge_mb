import ELK from 'elkjs/lib/elk.bundled.js';

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = '';
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', chunk => { data += chunk; });
    process.stdin.on('end', () => resolve(data));
    process.stdin.on('error', reject);
  });
}

try {
  const raw = await readStdin();
  const payload = JSON.parse(raw);
  const elk = new ELK();
  const children = payload.nodes.map(n => ({
    id: n.id,
    width: n.width,
    height: n.height,
    ports: (n.ports || []).map(p => ({
      id: p.id,
      width: 1,
      height: 1,
      properties: {
        'org.eclipse.elk.port.side': p.side
      }
    })),
    properties: (n.ports && n.ports.length) ? {
      'org.eclipse.elk.portConstraints': 'FIXED_SIDE'
    } : {}
  }));
  const edges = payload.edges.map(e => ({
    id: e.id,
    sources: [e.source_port || e.source],
    targets: [e.target_port || e.target]
  }));
  const graph = {
    id: payload.id || 'scene',
    children,
    edges,
    properties: {
      'org.eclipse.elk.algorithm': 'layered',
      'org.eclipse.elk.direction': payload.direction,
      'org.eclipse.elk.edgeRouting': 'ORTHOGONAL',
      'org.eclipse.elk.spacing.nodeNode': payload.spacing?.nodeNode ?? 50,
      'org.eclipse.elk.layered.spacing.nodeNodeBetweenLayers': payload.spacing?.nodeNodeBetweenLayers ?? 80,
      'org.eclipse.elk.spacing.edgeNode': payload.spacing?.edgeNode ?? 20,
      'org.eclipse.elk.spacing.edgeEdge': payload.spacing?.edgeEdge ?? 12,
      'org.eclipse.elk.randomSeed': 7
    }
  };
  const result = await elk.layout(graph);
  process.stdout.write(JSON.stringify(result));
} catch (err) {
  process.stderr.write(String(err && err.stack ? err.stack : err));
  process.exit(1);
}
