import { useEffect, useRef, useState } from 'react';

const Starfield = () => {
  const canvasRef = useRef(null);
  const starsRef = useRef([]);
  const mouseRef = useRef({ x: 0, y: 0, targetX: 0, targetY: 0 });
  const animationRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    
    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
      setDimensions({ width: canvas.width, height: canvas.height });
      initStars();
    };

    const initStars = () => {
      const starCount = Math.floor((canvas.width * canvas.height) / 3000);
      const stars = [];
      
      for (let i = 0; i < starCount; i++) {
        stars.push({
          x: Math.random() * canvas.width,
          y: Math.random() * canvas.height,
          size: Math.random() * 2 + 0.5,
          baseX: 0,
          baseY: 0,
          brightness: Math.random() * 0.5 + 0.3,
          twinkleSpeed: Math.random() * 0.02 + 0.005,
          twinklePhase: Math.random() * Math.PI * 2,
          depth: Math.random() * 0.5 + 0.1, // Depth factor for parallax
        });
      }
      
      starsRef.current = stars;
    };

    const handleMouseMove = (e) => {
      mouseRef.current.targetX = e.clientX;
      mouseRef.current.targetY = e.clientY;
    };

    const animate = () => {
      ctx.fillStyle = '#0a0a1a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      // Smooth mouse interpolation
      mouseRef.current.x += (mouseRef.current.targetX - mouseRef.current.x) * 0.05;
      mouseRef.current.y += (mouseRef.current.targetY - mouseRef.current.y) * 0.05;

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const mouseOffsetX = (mouseRef.current.x - centerX) / centerX;
      const mouseOffsetY = (mouseRef.current.y - centerY) / centerY;

      starsRef.current.forEach((star) => {
        // Calculate twinkle effect
        star.twinklePhase += star.twinkleSpeed;
        const twinkle = Math.sin(star.twinklePhase) * 0.3 + 0.7;
        
        // Calculate parallax offset based on mouse position and star depth
        const parallaxX = mouseOffsetX * 50 * star.depth;
        const parallaxY = mouseOffsetY * 50 * star.depth;

        // Draw star with glow effect
        const gradient = ctx.createRadialGradient(
          star.x + parallaxX,
          star.y + parallaxY,
          0,
          star.x + parallaxX,
          star.y + parallaxY,
          star.size * 2
        );
        
        // Calming blue-white colors
        const hue = Math.random() * 40 + 200; // Blue to cyan range
        const saturation = Math.random() * 20 + 30;
        const lightness = 60 + star.brightness * 40;
        
        gradient.addColorStop(0, `hsla(${hue}, ${saturation}%, ${lightness}%, ${twinkle})`);
        gradient.addColorStop(0.4, `hsla(${hue}, ${saturation}%, ${lightness * 0.6}%, ${twinkle * 0.6})`);
        gradient.addColorStop(1, 'transparent');
        
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(
          star.x + parallaxX,
          star.y + parallaxY,
          star.size * 2,
          0,
          Math.PI * 2
        );
        ctx.fill();

        // Draw bright center
        ctx.fillStyle = `hsla(${hue}, ${saturation - 10}%, 90%, ${twinkle})`;
        ctx.beginPath();
        ctx.arc(
          star.x + parallaxX,
          star.y + parallaxY,
          star.size * 0.5,
          0,
          Math.PI * 2
        );
        ctx.fill();
      });

      // Draw subtle nebula clouds
      drawNebula(ctx, canvas.width, canvas.height, mouseOffsetX, mouseOffsetY);

      animationRef.current = requestAnimationFrame(animate);
    };

    const drawNebula = (ctx, width, height, offsetX, offsetY) => {
      const time = Date.now() * 0.0001;
      
      // Subtle purple/blue nebula
      const gradient1 = ctx.createRadialGradient(
        width * 0.3 + offsetX * 30,
        height * 0.4 + offsetY * 30,
        0,
        width * 0.3 + offsetX * 30,
        height * 0.4 + offsetY * 30,
        width * 0.4
      );
      gradient1.addColorStop(0, 'rgba(100, 80, 180, 0.03)');
      gradient1.addColorStop(0.5, 'rgba(60, 50, 120, 0.02)');
      gradient1.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient1;
      ctx.fillRect(0, 0, width, height);

      // Subtle blue nebula
      const gradient2 = ctx.createRadialGradient(
        width * 0.7 + offsetX * 20,
        height * 0.6 + offsetY * 20,
        0,
        width * 0.7 + offsetX * 20,
        height * 0.6 + offsetY * 20,
        width * 0.35
      );
      gradient2.addColorStop(0, 'rgba(40, 80, 140, 0.025)');
      gradient2.addColorStop(0.5, 'rgba(30, 60, 100, 0.015)');
      gradient2.addColorStop(1, 'transparent');
      ctx.fillStyle = gradient2;
      ctx.fillRect(0, 0, width, height);
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    window.addEventListener('mousemove', handleMouseMove);
    animate();

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('mousemove', handleMouseMove);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        zIndex: -1,
        cursor: 'none',
      }}
    />
  );
};

export default Starfield;
