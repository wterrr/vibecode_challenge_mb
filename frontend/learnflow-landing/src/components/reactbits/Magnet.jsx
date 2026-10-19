// From React Bits (David Haz), Magnet component, MIT + Commons Clause license.
// Source: https://github.com/DavidHDev/react-bits/blob/main/src/content/Animations/Magnet/Magnet.jsx
import {useState,useEffect,useRef} from 'react';
export default function Magnet({children,padding=70,disabled=false,magnetStrength=8,activeTransition='transform .3s ease-out',inactiveTransition='transform .5s ease-in-out',wrapperClassName='',innerClassName='',...props}){
  const [active,setActive]=useState(false),[pos,setPos]=useState({x:0,y:0}),ref=useRef(null);
  useEffect(()=>{if(disabled){setPos({x:0,y:0});return;}
    const listener=e=>{if(!ref.current)return;const {left,top,width,height}=ref.current.getBoundingClientRect();const cx=left+width/2,cy=top+height/2;
      if(Math.abs(cx-e.clientX)<width/2+padding&&Math.abs(cy-e.clientY)<height/2+padding){setActive(true);setPos({x:(e.clientX-cx)/magnetStrength,y:(e.clientY-cy)/magnetStrength});}else{setActive(false);setPos({x:0,y:0});}};
    window.addEventListener('mousemove',listener);return()=>window.removeEventListener('mousemove',listener);
  },[padding,disabled,magnetStrength]);
  return <div ref={ref} className={wrapperClassName} style={{position:'relative',display:'inline-block'}} {...props}><div className={innerClassName} style={{transform:`translate3d(${pos.x}px,${pos.y}px,0)`,transition:active?activeTransition:inactiveTransition}}>{children}</div></div>;
}
