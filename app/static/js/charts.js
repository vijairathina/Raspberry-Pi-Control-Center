// Real-time Chart.js helper library for Raspberry Pi Control Center

const RPiCharts = {
  createLineChart(canvasId, label, colorHex, initialLabels = [], initialData = []) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx || typeof Chart === 'undefined') return null;

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: initialLabels,
        datasets: [{
          label: label,
          data: initialData,
          borderColor: colorHex,
          backgroundColor: colorHex + '22',
          borderWidth: 2,
          fill: true,
          tension: 0.35,
          pointRadius: 1,
          pointHoverRadius: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: '#111827',
            borderColor: 'rgba(255,255,255,0.1)',
            borderWidth: 1
          }
        },
        scales: {
          x: {
            grid: { display: false, color: 'rgba(255,255,255,0.05)' },
            ticks: { color: '#9ca3af', font: { size: 10 }, maxTicksLimit: 6 }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.06)' },
            ticks: { color: '#9ca3af', font: { size: 10 } },
            suggestedMin: 0,
            suggestedMax: 100
          }
        }
      }
    });
  },

  createDualLineChart(canvasId, label1, color1, label2, color2, initialLabels = [], data1 = [], data2 = []) {
    const ctx = document.getElementById(canvasId)?.getContext('2d');
    if (!ctx || typeof Chart === 'undefined') return null;

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: initialLabels,
        datasets: [
          {
            label: label1,
            data: data1,
            borderColor: color1,
            backgroundColor: color1 + '15',
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 0
          },
          {
            label: label2,
            data: data2,
            borderColor: color2,
            backgroundColor: color2 + '15',
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { color: '#9ca3af', boxWidth: 12, font: { size: 11 } }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#9ca3af', font: { size: 10 }, maxTicksLimit: 6 }
          },
          y: {
            grid: { color: 'rgba(255,255,255,0.06)' },
            ticks: { color: '#9ca3af', font: { size: 10 } }
          }
        }
      }
    });
  },

  updateLineChart(chart, labels, data) {
    if (!chart) return;
    chart.data.labels = labels;
    chart.data.datasets[0].data = data;
    chart.update('none');
  },

  updateDualLineChart(chart, labels, data1, data2) {
    if (!chart) return;
    chart.data.labels = labels;
    chart.data.datasets[0].data = data1;
    chart.data.datasets[1].data = data2;
    chart.update('none');
  }
};
