export default function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200 mt-auto">
      <div className="container mx-auto px-4 py-6 max-w-6xl text-center text-gray-500 text-sm">
        <p>© {new Date().getFullYear()} KingBlog. 记录每一天的思考与成长.</p>
      </div>
    </footer>
  );
}

