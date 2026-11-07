module.exports = {
    content: {
        relative: true,
        files: ['./app/templates/**/*.html', './app/api/**/*.py', './static/js/**/*.js'],
    },
    // Runtime feedback and controls use these classes outside template markup.
    safelist: [
        'hidden', 'text-gray-500', 'text-gray-600', 'text-blue-600',
        'text-amber-600', 'text-green-600', 'text-red-600', 'text-red-700',
        'bg-amber-500', 'bg-blue-500', 'bg-blue-600', 'bg-red-500', 'bg-white',
        'text-white', 'border-b-2', 'border-blue-600',
    ],
};
