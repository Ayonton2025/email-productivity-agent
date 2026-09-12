import { useEffect, useRef } from 'react'

const BackgroundCanvas = ({ scrollY }) => {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return undefined

    const context = canvas.getContext('2d')
    let animationId
    let time = 0

    const resizeCanvas = () => {
      canvas.width = canvas.offsetWidth
      canvas.height = canvas.offsetHeight
    }

    const drawAnimation = () => {
      context.fillStyle = 'rgba(255, 255, 255, 0.03)'
      context.fillRect(0, 0, canvas.width, canvas.height)
      context.strokeStyle = 'rgba(99, 102, 241, 0.2)'
      context.lineWidth = 1

      for (let index = 0; index < 5; index += 1) {
        const x = Math.sin(time * 0.001 + index) * 100 + canvas.width / 2 + scrollY * 0.1
        const y = Math.cos(time * 0.0008 + index) * 100 + canvas.height / 2
        context.beginPath()
        context.arc(
          x,
          y,
          (index === 0 ? 50 : 30) + Math.sin(time * (index === 0 ? 0.002 : 0.003) + index) * (index === 0 ? 20 : 15),
          0,
          Math.PI * 2
        )
        context.stroke()
      }

      time += 1
      animationId = requestAnimationFrame(drawAnimation)
    }

    resizeCanvas()
    window.addEventListener('resize', resizeCanvas)
    drawAnimation()

    return () => {
      window.removeEventListener('resize', resizeCanvas)
      cancelAnimationFrame(animationId)
    }
  }, [scrollY])

  return <canvas ref={canvasRef} className="bg-canvas"></canvas>
}

export default BackgroundCanvas
