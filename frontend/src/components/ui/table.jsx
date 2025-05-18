export function Table({ headers, rows }) {
  return (
    <table className="w-full border border-gray-400 mt-5">
      <thead>
        <tr>
          {headers.map((header, idx) => (
            <th
              key={idx}
              className="border border-gray-400 bg-indigo-600 text-white p-3"
            >
              {header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, idx) => (
          <tr key={idx} className="bg-white hover:bg-indigo-50">
            {row.map((cell, i) => (
              <td key={i} className="border border-gray-300 p-3 text-center">
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
