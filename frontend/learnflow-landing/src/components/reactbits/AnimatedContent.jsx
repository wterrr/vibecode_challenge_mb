// From React Bits (David Haz), AnimatedContent component, MIT + Commons Clause license.
// Source: https://github.com/DavidHDev/react-bits/blob/main/src/content/Animations/AnimatedContent/AnimatedContent.jsx
import {useRef,useEffect} from 'react';
import {gsap} from 'gsap';
import {ScrollTrigger} from 'gsap/ScrollTrigger';
gsap.registerPlugin(ScrollTrigger);
export default function AnimatedContent({children,container,distance=45,direction='vertical',reverse=false,duration=.8,ease='power3.out',initialOpacity=0,animateOpacity=true,scale=1,threshold=.12,delay=0,className='',...props}){
 const ref=useRef(null);
 useEffect(()=>{const el=ref.current;if(!el)return;
  // Accessibility: reduced motion should not hide scroll sections.
  if(window.matchMedia('(prefers-reduced-motion: reduce)').matches){gsap.set(el,{clearProps:'all',visibility:'visible',opacity:1});return;}
  let target=container||null;if(typeof target==='string')target=document.querySelector(target);
  const axis=direction==='horizontal'?'x':'y',offset=reverse?-distance:distance,startPct=(1-threshold)*100;
  gsap.set(el,{[axis]:offset,scale,opacity:animateOpacity?initialOpacity:1,visibility:'visible'});
  const tl=gsap.timeline({paused:true,delay});tl.to(el,{[axis]:0,scale:1,opacity:1,duration,ease});
  const st=ScrollTrigger.create({trigger:el,scroller:target,start:`top ${startPct}%`,once:true,onEnter:()=>tl.play()});
  return()=>{st.kill();tl.kill();};
 },[container,distance,direction,reverse,duration,ease,initialOpacity,animateOpacity,scale,threshold,delay]);
 return <div ref={ref} className={className} style={{visibility:'hidden'}} {...props}>{children}</div>;
}
