interface UserMessageProps {
  content: string;
}

export default function UserMessage({ content }: UserMessageProps) {
  return (
    <div className="flex justify-end">
      <div
        className="max-w-lg rounded-lg px-4 py-2 text-sm text-white"
        style={{
          backgroundColor: "#1C1C1C",
          border: "1px solid #2A2A2A",
        }}
      >
        {content}
      </div>
    </div>
  );
}
