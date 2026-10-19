// From React Bits (David Haz), ClickSpark component, MIT + Commons Clause license.
// Source: https://github.com/DavidHDev/react-bits/blob/main/src/content/Animations/ClickSpark/ClickSpark.jsx
'use client';
import { useRef, useEffect, useCallback } from 'react';
const ClickSpark = ({sparkColor='#fff',sparkSize=10,sparkRadius=15,sparkCount=8,duration=400,easing='ease-out',extraScale=1,children}) => {
  const canvasRef=useRef(null), sparksRef=useRef([]),startTimeRef=useRef(null);
  useEffect(()=>{
    const canvas=canvasRef.current,parent=canvas?.parentElement;if(!parent)return;
    let resizeTimeout;
    const resizeCanvas=()=>{const {width,height}=parent.getBoundingClientRect();if(canvas.width!==Math.ceil(width)||canvas.height!==Math.ceil(height)){canvas.width=Math.ceil(width);canvas.height=Math.ceil(height);}};
    const ro=new ResizeObserver(()=>{clearTimeout(resizeTimeout);resizeTimeout=setTimeout(resizeCanvas,100);});ro.observe(parent);resizeCanvas();
    return()=>{ro.disconnect();clearTimeout(resizeTimeout);};
  },[]);
  const easeFunc=useCallback(t=>easing==='linear'?t:easing==='ease-in'?t*t:easing==='ease-in-out'?(t<.5?2*t*t:-1+(4-2*t)*t):t*(2-t),[easing]);
  useEffect(()=>{const canvas=canvasRef.current;if(!canvas)return;const ctx=canvas.getContext('2d');let id;
    const draw=ts=>{if(!startTimeRef.current)startTimeRef.current=ts;ctx.clearRect(0,0,canvas.width,canvas.height);
      sparksRef.current=sparksRef.current.filter(s=>{const elapsed=ts-s.startTime;if(elapsed>=duration)return false;const progress=elapsed/duration,eased=easeFunc(progress),distance=eased*sparkRadius*extraScale,len=sparkSize*(1-eased),x1=s.x+distance*Math.cos(s.angle),y1=s.y+distance*Math.sin(s.angle);
        ctx.strokeStyle=sparkColor;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x1+len*Math.cos(s.angle),y1+len*Math.sin(s.angle));ctx.stroke();return true;});
      id=requestAnimationFrame(draw);};id=requestAnimationFrame(draw);return()=>cancelAnimationFrame(id);
  },[sparkColor,sparkSize,sparkRadius,duration,easeFunc,extraScale]);
  const click=e=>{const rect=canvasRef.current?.getBoundingClientRect();if(!rect)return;const now=performance.now();sparksRef.current.push(...Array.from({length:sparkCount},(_,i)=>({x:e.clientX-rect.left,y:e.clientY-rect.top,angle:Math.PI*2*i/sparkCount,startTime:now})));};
  return <div className="click-spark" onClick={click} style={{position:'relative',width:'100%'}}><canvas ref={canvasRef} style={{position:'absolute',width:'100%',height:'100%',top:0,left:0,pointerEvents:'none',zIndex:4}}/>{children}</div>;
};
export default ClickSpark;
