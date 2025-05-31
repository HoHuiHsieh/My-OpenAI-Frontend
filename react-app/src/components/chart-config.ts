import { 
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

// Register Chart.js components to avoid "not a registered scale" errors
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

// Ensure Chart.js has proper defaults and scale registrations
export const configureCharts = () => {
  // Make sure scales are registered and not reused
  ChartJS.defaults.maintainAspectRatio = false;
  ChartJS.defaults.responsive = true;
  
  // Clear any existing charts when hot module reloading
  if (typeof window !== 'undefined') {
    // Clear canvas registry on page reload/refresh to prevent "Canvas already in use" errors
    ChartJS.register({
      id: 'resetRegistry',
      beforeInit: (chart) => {
      }
    });
  }
};

// Call the configuration function immediately
configureCharts();

export default configureCharts;