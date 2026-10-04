#!/usr/bin/env python3
"""Create isolated experimental copies; never modify package source."""
import pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[2];source=(ROOT/'src/mdx.f').read_text()
chunks=re.split(r'(?=    (?:private )?fn\()',source);result=[]
for chunk in chunks:
 if 'source.data' in chunk and re.match(r'    (?:private )?fn\(\w+\(source[,)]',chunk):
  chunk=chunk.replace('source.data','source_bytes_view.data');idx=chunk.index('{')+1;chunk=chunk[:idx]+'\n        source_bytes_view := {"data":source.data}\n'+chunk[idx:]
 elif chunk.startswith('    private fn(parse_core('):
  chunk=chunk.replace('source.data','source_bytes_view.data');needle='source := {"raw":value,"data":encoded,"length":encoded.length(),"limits":limits}\n';chunk=chunk.replace(needle,needle+'        source_bytes_view := {"data":source.data}\n')
 result.append(chunk)
pathlib.Path('/tmp/mdx-byte-view.f').write_text(''.join(result))
# Only in the experiment: remove the syntax-count ceiling to inspect the rejected page.
pathlib.Path('/tmp/mdx-uncapped.f').write_text(source.replace('>= 1024','>= 16384'))
# Inclusive timers add perturbation; compare uninstrumented timing separately.
fields=[];result=[];selected={'line_info','backtick_matches','frontmatter','fence','scan_js','jsx','point','node','attribute','plain_end','jsx_name','import_specifier'}
for chunk in chunks:
 match=re.match(r'    (?:private )?fn\((\w+)\(',chunk)
 if match and match[1] in selected:
  name=match[1];fields+=['    phase_'+name+' := 0','    calls_'+name+' := 0'];idx=chunk.index('{')+1;chunk=chunk[:idx]+'\n        phase_watch := timer(); phase_watch.start()\n'+chunk[idx:]
  chunk=chunk.replace('return ', 'phase_watch.stop(); this.phase_'+name+' += phase_watch.elapsed(); this.calls_'+name+' += 1; return ')
 result.append(chunk)
s=''.join(result).replace('    profile_name := "bounded"','    profile_name := "bounded"\n'+'\n'.join(fields))
pathlib.Path('/tmp/mdx-instrumented.f').write_text(s)

# Ablations change the preservation contract and must never be shipped.
no_positions=source.replace('return {"start":this.point(lines, begin),"end":this.point(lines, end)}','return {"start":null,"end":null}')
pathlib.Path('/tmp/mdx-no-positions.f').write_text(no_positions)
no_nodes=source.replace('return {"type":kind,"source":raw,"name":name,"value":value,"attributes":attributes,"children":children,"position":position}','return null').replace('return {"name":name,"kind":kind,"value":value,"source":raw,"position":position}','return null')
pathlib.Path('/tmp/mdx-no-nodes.f').write_text(no_nodes)
midpoint=source.replace('((low + high) / 2).floor().to_int()','((low + high) / 2).floor()')
pathlib.Path('/tmp/mdx-simple-midpoint.f').write_text(midpoint)
pathlib.Path('/tmp/mdx-midpoint-typed.f').write_text(midpoint.replace('"line":low + 1','"line":(low + 1).to_int()'))
